"""TARA Assistant UI — dashboard wireframe.

Sidebar ...... brand, numbered pipeline nav (Home, 7 steps, Knowledge Base,
               Settings), reviewer, API status, human-review disclaimer.
Header ....... title + subtitle, project selector.
Stepper ...... 7 numbered stages (done / current / todo) under the header.
Step 1 ....... upload card | parsed SVG diagram | system info; then assets /
               attack-surface / trust-boundary tables; then data flows /
               next-step / quick-summary cards.
Steps 2-6 .... shared master-detail review (list | detail + decisions).
Step 7 ....... traceability links + gaps, document preview, download, audit.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Streamlit puts this script's folder (ui/) on sys.path, not its parent,
# so make the Code/ package root importable regardless of launch directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import streamlit as st

from app.schemas import Architecture
from app.services.assets import data_flows, trust_boundaries
from app.services.lifecycle import mapping_status
from ui.diagram import render_architecture_svg

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "900"))

# One shared client: connection reuse + fast failure. The old per-call client
# with a 120 s timeout froze the whole UI whenever the backend was slow/down.
_client = httpx.Client(timeout=API_TIMEOUT)


@st.cache_data(ttl=30, show_spinner=False)
def _cached_health() -> dict:
    """Backend liveness, cached 30 s so navigation never waits on it."""
    resp = _client.get(f"{API_URL}/health", timeout=5)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=5, show_spinner=False)
def _cached_get(path: str):
    """GET through a short-lived cache so every rerun (i.e. every click) does
    not re-hit the backend; cleared automatically on any POST below."""
    resp = _client.get(f"{API_URL}{path}")
    resp.raise_for_status()
    return resp.json() if "json" in resp.headers.get("content-type", "") else resp.text

PILL = {
    "pending": "#64748b",
    "approved": "#16a34a",
    "rejected": "#dc2626",
    "needs_expert_review": "#d97706",
    "External": "#dc2626",
    "Vehicle Internal": "#16a34a",
    "External/Service": "#7c3aed",
}

STEP_DEFS = [
    ("Architecture Input", "Upload system architecture"),
    ("Assets & Attack Surface", "Identify assets and interfaces"),
    ("Threat Scenarios", "Find relevant threats"),
    ("Risk Assessment", "Assess impact and feasibility"),
    ("Mitigations", "Recommend controls"),
    ("Traceability", "Link to requirements"),
    ("Report", "Generate output"),
]
NAV = ["Home"] + [f"{i + 1}. {name}" for i, (name, _) in enumerate(STEP_DEFS)] + ["Knowledge Base", "Settings"]

# Router prefixes are plural (and risk uses /assess); never derive from item_type.
SUGGEST_PATHS = {
    "asset": "/assets/suggest",
    "threat": "/threats/suggest",
    "risk": "/risks/assess",
    "mitigation": "/mitigations/suggest",
}

# Every backend path the UI depends on, checked against the live API below.
REQUIRED_PATHS = sorted(set(SUGGEST_PATHS.values()) | {
    "/architecture/validate", "/assets/attack-surface", "/assets", "/threats",
    "/risks", "/mitigations", "/verifications", "/report/traceability",
    "/report/export", "/report/metrics", "/review/audit",
})


@st.cache_data(ttl=60, show_spinner=False)
def _api_paths() -> set:
    """Live route set from the backend's OpenAPI schema."""
    resp = _client.get(f"{API_URL}/openapi.json", timeout=10)
    resp.raise_for_status()
    return set(resp.json()["paths"])


def check_contract() -> None:
    """Fail visibly if the UI is newer/older than the running API.

    This is what turns a stale-terminal mystery (“buttons 404 forever”) into
    one line telling you to restart the API terminal.
    """
    try:
        missing = [p for p in REQUIRED_PATHS if p not in _api_paths()]
    except httpx.HTTPError:
        return  # backend down is already reported by the sidebar status
    if missing:
        st.sidebar.error("UI/API mismatch — restart the API terminal so it serves: "
                         + ", ".join(missing))

st.set_page_config(page_title="TARA Assistant", page_icon="🚗", layout="wide")
st.markdown(
    """<style>
    section[data-testid="stSidebar"] { background:#0f1f3d; }
    section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
    .pill { display:inline-block; padding:2px 10px; border-radius:999px;
            font-size:0.75rem; font-weight:600; color:#fff; }
    .stat-num { font-size:1.6rem; font-weight:700; color:#0f172a; }
    .stat-label { font-size:0.8rem; color:#64748b; }
    .step-num { display:inline-flex; width:28px; height:28px; border-radius:50%;
                align-items:center; justify-content:center; font-weight:700;
                font-size:0.85rem; color:#fff; }
    .step-name { font-size:0.8rem; font-weight:600; color:#0f172a; }
    .step-sub { font-size:0.7rem; color:#64748b; }
    </style>""",
    unsafe_allow_html=True,
)


def api(method: str, path: str, payload: dict | None = None, strict: bool = True):
    """GETs go through a 5 s cache (navigation stays instant); POSTs act and
    invalidate the cache, so the next render always shows fresh state.

    strict=False turns failures into a warning toast and returns None, for
    best-effort calls (e.g. auto-suggest during upload) that must not block
    the deterministic pipeline when the LLM provider is down.
    """
    if method == "GET":
        try:
            return _cached_get(path)
        except httpx.ConnectError:
            _backend_down()
    try:
        resp = _client.request(method, f"{API_URL}{path}", json=payload)
        resp.raise_for_status()
        _cached_get.clear()
        return resp.json() if "json" in resp.headers.get("content-type", "") else resp.text
    except httpx.ConnectError:
        _backend_down()
    except httpx.HTTPError as exc:
        detail = None
        if getattr(exc, "response", None) is not None:
            try:
                detail = exc.response.json().get("detail")
            except Exception:
                detail = exc.response.text
        if not strict:
            st.toast(f"Skipped (provider issue): {detail or exc}")
            return None
        st.error(f"API error: {detail or exc}")
        st.stop()


def _backend_down():
    """Fail fast with the exact fix instead of a frozen faded page."""
    st.error(f"Backend not reachable at {API_URL} — is the API terminal still running? "
             f"(venv\\Scripts\\python -m uvicorn app.main:app --app-dir "
             f"PCCOE_StudentName_PRN_CSx_AIML\\Code)")
    st.stop()


def pill(status: str) -> str:
    """Coloured badge; unknown values fall back to grey."""
    return (f'<span class="pill" style="background:{PILL.get(status, "#64748b")}">'
            f'{status.replace("_", " ")}</span>')


def reviewer() -> str:
    """Reviewer name; defaults to anonymous rather than blocking."""
    return st.session_state.get("reviewer", "").strip() or "anonymous"


def reviewed(item: dict) -> bool:
    """True once a human has approved or rejected the item."""
    return item.get("status") in ("approved", "rejected")


def goto(label: str) -> None:
    """Navigate to a sidebar destination and refresh."""
    st.session_state["page"] = label
    st.rerun()


def decide(item_type: str, item_id: str, decision: str, note: str = "", updates: dict | None = None) -> None:
    """Send one review decision, toast, and refresh."""
    api("POST", f"/review/{item_type}/{item_id}",
        {"decision": decision, "reviewer": reviewer(), "note": note, "updates": updates or {}})
    st.toast(f"{decision.title()}: {item_id}")
    st.rerun()


def trust_level(interface: dict, reason: str) -> str:
    """Trust pill for an exposed interface: service > external > internal."""
    blob = f"{interface['protocol']} {interface['name']} {reason}".lower()
    if any(k in blob for k in ("uds", "jtag", "diagnostic", "tester", "uart")):
        return "External/Service"
    return "External"


def detail_panel(item_type: str, item: dict) -> None:
    """Right-hand detail: full fields, sources, and all review actions."""
    title = item.get("title") or item.get("name") or item.get("id")
    st.markdown(f"### {title}")
    st.markdown(f"`{item['id']}` &nbsp; {pill(item.get('status', 'pending'))}", unsafe_allow_html=True)
    st.write(item.get("description", ""))
    for key in ("stride_category", "affected_assets", "cybersecurity_requirement",
                "impact_value", "feasibility_value", "risk_value", "rationale",
                "reviewer", "review_note"):
        if item.get(key) not in (None, "", [], {}):
            st.markdown(f"**{key.replace('_', ' ')}:** `{item[key]}`")
    sources = ", ".join(f"`{s}`" for s in item.get("source_ids", [])) or "*uncited — needs expert review*"
    st.caption(f"Sources: {sources}")
    if item_type == "mitigation":
        verification_block(item)
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("✅ Approve", key=f"ok-{item_type}-{item['id']}", use_container_width=True):
        decide(item_type, item["id"], "approve")
    if c2.button("❌ Reject", key=f"no-{item_type}-{item['id']}", use_container_width=True):
        decide(item_type, item["id"], "reject")
    with st.expander("✏️ Edit with note"):
        with st.form(key=f"edit-{item_type}-{item['id']}"):
            note = st.text_input("Review note")
            desc = st.text_area("Description", value=item.get("description", ""))
            if st.form_submit_button("Save edit"):
                decide(item_type, item["id"], "edit", note, {"description": desc})


def verification_block(item: dict) -> None:
    """Verifications linked to this mitigation, plus a creation form."""
    vers = [v for v in api("GET", "/verifications") if v["mitigation_id"] == item["id"]]
    st.markdown("**🔬 Verifications (mitigation → test)**")
    if vers:
        st.dataframe([{"id": v["id"], "method": v["test_method"],
                       "result": v["status_detail"], "review": v.get("status", "pending")}
                      for v in vers], use_container_width=True, hide_index=True)
    else:
        st.caption("No verification linked yet — this is a traceability gap.")
    with st.form(key=f"ver-{item['id']}"):
        method = st.text_input("Test method", placeholder="e.g. HIL fault injection on CAN")
        if st.form_submit_button("Link verification"):
            if not method.strip():
                st.warning("Describe the test method first.")
            else:
                vid = f"VER-{item['id']}-{len(vers) + 1}"
                api("POST", "/verifications",
                    {"id": vid, "mitigation_id": item["id"], "test_method": method,
                     "reviewer": reviewer()})
                st.toast(f"Linked {vid}")
                st.rerun()


def review_step(item_type: str, items: list[dict], suggest_label: str, suggest_payload: dict | None) -> None:
    """Master-detail review: toolbar + progress; filterable list | detail."""
    done = sum(1 for i in items if reviewed(i))
    t1, t2 = st.columns([3, 1])
    with t1:
        if st.button(f"✨ {suggest_label}", type="primary", disabled=suggest_payload is None):
            with st.spinner("Consulting the threat library…"):
                api("POST", SUGGEST_PATHS[item_type], suggest_payload)
            st.rerun()
    with t2:
        st.metric("Reviewed", f"{done}/{len(items)}")
    st.progress(done / len(items) if items else 0.0)

    filt = st.selectbox("Filter", ["Needs review", "All", "Approved", "Rejected"], key=f"filter-{item_type}")
    visible = items if filt == "All" else (
        [i for i in items if not reviewed(i)] if filt == "Needs review"
        else [i for i in items if i.get("status") == filt.lower()])
    if not visible:
        st.info("Nothing in this view — change the filter or run the suggest step.")
        return
    left, right = st.columns([2, 3])
    with left:
        options = {f"{'●' if reviewed(i) else '○'} {(i.get('title') or i.get('name') or i['id'])[:45]}": i["id"]
                   for i in visible}
        label = st.radio("Items", list(options), key=f"radio-{item_type}")
        st.session_state[f"selected-{item_type}"] = options[label]
    with right:
        with st.container(border=True):
            detail_panel(item_type, next(i for i in items if i["id"] == st.session_state[f"selected-{item_type}"]))


def step_done(name: str, assets: list, threats: list, risks: list, mits: list) -> bool:
    """A step counts as done when its items exist and are all reviewed."""
    groups = {"Assets & Attack Surface": assets, "Threat Scenarios": threats,
              "Risk Assessment": risks, "Mitigations": mits,
              "Traceability": assets + threats, "Report": assets + threats}
    items = groups.get(name, [])
    if name == "Architecture Input":
        return st.session_state.get("architecture") is not None
    return bool(items) and all(reviewed(i) for i in items)


def stepper(page: str, assets: list, threats: list, risks: list, mits: list) -> None:
    """Seven numbered stages with done / current / todo states; numbers navigate."""
    cols = st.columns(7)
    current_idx = next((i for i, (n, _) in enumerate(STEP_DEFS) if page.endswith(n)), -1)
    for i, ((name, sub), col) in enumerate(zip(STEP_DEFS, cols)):
        done = step_done(name, assets, threats, risks, mits)
        color = "#16a34a" if done else ("#1d4ed8" if i == current_idx else "#cbd5e1")
        with col:
            if st.button(f"{'✓' if done else i + 1}", key=f"step-{i}"):
                goto(f"{i + 1}. {name}")
            st.markdown(f'<span class="step-num" style="background:{color}">'
                        f'{"✓" if done else i + 1}</span> '
                        f'<span class="step-name">{name}</span><br>'
                        f'<span class="step-sub">{sub}</span>', unsafe_allow_html=True)


def prev_next(idx: int) -> None:
    """Back / Next pipeline buttons at the bottom of steps 1-6."""
    _, back, fwd, _ = st.columns([6, 2, 2, 6])
    if back.button("← Back", key=f"back-{idx}", use_container_width=True):
        goto(NAV[idx - 1] if idx > 1 else "Home")
    if fwd.button("Next →", key=f"fwd-{idx}", type="primary", use_container_width=True):
        goto(NAV[idx + 1])


# ---------------------------------------------------------------- data -----
assets = api("GET", "/assets")
threats = api("GET", "/threats")
risks = api("GET", "/risks")
mitigations = api("GET", "/mitigations")
report = api("GET", "/report/traceability")

# ------------------------------------------------------------- sidebar -----
st.sidebar.markdown("## 🚗 Automotive Cybersecurity")
st.sidebar.caption("TARA Assistant")
for label in NAV:
    active = st.session_state.get("page", "Home") == label
    if st.sidebar.button(("▶ " if active else "") + label, key=f"nav-{label}", use_container_width=True):
        goto(label)
st.sidebar.divider()
st.sidebar.text_input("Reviewer", key="reviewer", placeholder="e.g. a.sharma")
try:
    _cached_health()
    st.sidebar.success("● API connected")
except httpx.HTTPError:
    st.sidebar.error(f"● API unreachable at {API_URL}")
check_contract()
st.sidebar.divider()
st.sidebar.markdown("🛡️ **AI-Assisted Tool**<br>Human Review Required")
st.sidebar.caption("AI-generated content must be reviewed by authorized cybersecurity "
                   "engineers before use for compliance or design approval.")

# -------------------------------------------------------------- header -----
h1, h2 = st.columns([4, 1])
with h1:
    st.title("Automotive Cybersecurity TARA Assistant")
    st.caption("AI-assisted threat analysis and risk assessment for vehicle systems")
with h2:
    project = st.selectbox("Project", ["TCU Demo"], key="project")
_ = project

page = st.session_state.get("page", "Home")
if page not in ("Home", "Knowledge Base", "Settings"):
    stepper(page, assets, threats, risks, mitigations)
    st.divider()

# ---------------------------------------------------------------- Home -----
if page == "Home":
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Assets", len(assets), border=True)
    k2.metric("Threat scenarios", len(threats), border=True)
    avg = round(sum(r["risk_value"] for r in risks) / len(risks), 1) if risks else 0.0
    k3.metric("Avg. risk value", avg, border=True)
    k4.metric("Open gaps", len(report["gaps"]), border=True)
    m = api("GET", "/report/metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Knowledge reuse (cited items)", f"{m['knowledge_reuse_pct']}%", border=True)
    m2.metric("Review completion", f"{m['review_completion_pct']}%", border=True)
    m3.metric("Chain completeness", f"{m['chain_completeness_pct']}%", border=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**Pipeline status**")
            rows = []
            for i, (name, _) in enumerate(STEP_DEFS):
                rows.append({"step": f"{i + 1}. {name}",
                             "state": "✅ done" if step_done(name, assets, threats, risks, mitigations) else "○ pending"})
            st.dataframe(rows, use_container_width=True, hide_index=True)
    with c2:
        with st.container(border=True):
            st.markdown("**Risk distribution**")
            if risks:
                st.bar_chart({v: sum(1 for r in risks if r["risk_value"] == v) for v in range(6)})
            else:
                st.info("No risks assessed yet.")
    with st.container(border=True):
        st.markdown("**Gaps needing attention**")
        st.dataframe(report["gaps"], use_container_width=True, hide_index=True)

# --------------------------------------------------- 1. Architecture -------
elif page == "1. Architecture Input":
    arch = st.session_state.get("architecture")
    surface = st.session_state.get("surface", [])
    boundaries = st.session_state.get("boundaries", [])
    flows = st.session_state.get("flows", [])

    c1, c2, c3 = st.columns([1.1, 1.8, 1.1])
    with c1:
        with st.container(border=True):
            st.markdown("**📤 Upload Architecture**")
            st.caption("Upload system architecture, communication matrix or interface "
                       "specification (JSON, XML).")
            fmt = st.selectbox("Format", ["json", "xml"])
            uploaded = st.file_uploader(f"Drag and drop .( {fmt} ) file or click to browse", type=[fmt])
            pasted = st.text_area("…or paste content", height=120)
            content = (uploaded.read().decode("utf-8") if uploaded else pasted).strip()
            if uploaded:
                st.success(f"{uploaded.name} · {uploaded.size / 1024:.1f} KB")
            if st.button("⚙️ Process Architecture", type="primary", use_container_width=True, disabled=not content):
                arch = api("POST", "/architecture/validate", {"content": content, "format": fmt})
                st.session_state["architecture"] = arch
                st.session_state["arch_raw"] = json.loads(content) if fmt == "json" else {}
                parsed = Architecture.model_validate(arch)
                st.session_state["surface"] = api("POST", "/assets/attack-surface", {"architecture": arch})
                st.session_state["boundaries"] = trust_boundaries(parsed)
                st.session_state["flows"] = data_flows(parsed)
                api("POST", "/assets/suggest", {"architecture": arch}, strict=False)
                st.toast("Architecture processed — surface mapped (suggestions need a working LLM provider)")
                goto("2. Assets & Attack Surface")
    with c2:
        with st.container(border=True):
            st.markdown("**🛠️ System Architecture (Parsed View)**")
            if arch:
                st.markdown(render_architecture_svg(Architecture.model_validate(arch)), unsafe_allow_html=True)
            else:
                st.info("Process an architecture to render the parsed diagram.")
    with c3:
        with st.container(border=True):
            st.markdown("**ℹ️ System Information**")
            if arch:
                raw = st.session_state.get("arch_raw", {})
                st.markdown(f"**System**&ensp;{raw.get('project', '—')}")
                st.markdown(f"**Version**&ensp;{raw.get('version', '—')}")
                st.markdown(f"**Total Components**&ensp;{len(arch['components'])}")
                st.markdown(f"**Total Interfaces**&ensp;{len(arch['interfaces'])}")
                st.markdown(f"**Trust Boundaries**&ensp;{len(boundaries)}")
                st.markdown(f"**Data Flows**&ensp;{len(flows)}")
                st.markdown("**Parsed Components**")
                for comp in arch["components"]:
                    st.markdown(f"{comp['name']} &ensp; {pill(comp['trust_boundary'])}", unsafe_allow_html=True)
            else:
                st.info("Nothing processed yet.")

    if arch:
        t1, t2, t3 = st.columns(3)
        with t1:
            with st.container(border=True):
                st.markdown("**🗄️ Identified Assets**")
                st.dataframe([{"#": n + 1, "asset": a["name"],
                               "protection": ", ".join(a.get("security_properties_required", [])),
                               "description": a.get("description", "")[:60]}
                              for n, a in enumerate(assets)] or [{"asset": "none yet — see step 2"}],
                             use_container_width=True, hide_index=True)
        with t2:
            with st.container(border=True):
                st.markdown("**🎯 Attack Surfaces**")
                st.dataframe([{"#": n + 1, "attack surface": e["interface"]["name"],
                               "interface": e["interface"]["protocol"],
                               "trust level": trust_level(e["interface"], e["reason"])}
                              for n, e in enumerate(surface)],
                             use_container_width=True, hide_index=True)
        with t3:
            with st.container(border=True):
                st.markdown("**🛡️ Trust Boundaries**")
                st.dataframe([{"#": n + 1, "boundary": b["boundary"],
                               "components": " ↔ ".join(b["components"])}
                              for n, b in enumerate(boundaries)],
                             use_container_width=True, hide_index=True)
        b1, b2, b3 = st.columns(3)
        with b1:
            with st.container(border=True):
                st.markdown("**🔀 Sample Data Flow**")
                st.dataframe([{"#": n + 1, "data flow": f["flow"]} for n, f in enumerate(flows[:3])],
                             use_container_width=True, hide_index=True)
        with b2:
            with st.container(border=True):
                st.markdown("**➡️ Next Step**")
                st.success("Architecture processed successfully. Proceed to identify threat "
                           "scenarios for the detected assets and attack surfaces.")
                if st.button("Go to Threat Scenarios →", type="primary", use_container_width=True):
                    goto("3. Threat Scenarios")
        with b3:
            with st.container(border=True):
                st.markdown("**📊 Quick Summary**")
                s1, s2 = st.columns(2)
                s1.markdown(f"<div class='stat-num'>{len(assets)}</div>"
                            f"<div class='stat-label'>🗄️ Assets Identified</div>", unsafe_allow_html=True)
                s2.markdown(f"<div class='stat-num'>{len(surface)}</div>"
                            f"<div class='stat-label'>🎯 Attack Surfaces</div>", unsafe_allow_html=True)
                s3, s4 = st.columns(2)
                s3.markdown(f"<div class='stat-num'>{len(boundaries)}</div>"
                            f"<div class='stat-label'>🛡️ Trust Boundaries</div>", unsafe_allow_html=True)
                s4.markdown(f"<div class='stat-num'>{len(flows)}</div>"
                            f"<div class='stat-label'>🔀 Data Flows</div>", unsafe_allow_html=True)
    prev_next(1)

# --------------------------------------------------- 2-5 review steps ----
elif page == "2. Assets & Attack Surface":
    arch = st.session_state.get("architecture")
    if not arch:
        st.warning("Process an architecture on step 1 first — suggestions need it.")
    else:
        review_step("asset", assets, "Suggest assets", {"architecture": arch})
    prev_next(2)

elif page == "3. Threat Scenarios":
    arch = st.session_state.get("architecture", {})
    review_step("threat", threats, "Suggest threats",
                {"assets": assets, "interfaces": arch.get("interfaces", [])} if assets else None)
    prev_next(3)

elif page == "4. Risk Assessment":
    st.caption("Impact × feasibility via the configured matrix — no LLM judgement involved.")
    if risks:
        st.bar_chart({v: sum(1 for r in risks if r["risk_value"] == v) for v in range(6)})
    review_step("risk", sorted(risks, key=lambda r: -r["risk_value"]), "Assess all threats",
                {"threats": threats} if threats else None)
    prev_next(4)

elif page == "5. Mitigations":
    review_step("mitigation", mitigations, "Suggest mitigations",
                {"threats": threats, "risks": risks} if threats else None)
    prev_next(5)

# ------------------------------------------------------ 6. Traceability ---
elif page == "6. Traceability":
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**Links (asset → threat → risk → mitigations → verifications)**")
            st.dataframe([{"asset": ln["asset_id"], "threat": ln["threat_id"],
                           "risk": ln["risk_id"] or "—",
                           "mitigations": ", ".join(ln["mitigation_ids"]) or "—",
                           "verifications": ", ".join(ln["verification_ids"]) or "—"}
                          for ln in report["links"]], use_container_width=True, hide_index=True)
    with c2:
        with st.container(border=True):
            st.markdown("**Gaps**")
            st.dataframe(report["gaps"], use_container_width=True, hide_index=True)
    prev_next(6)

# ----------------------------------------------------------- 7. Report ---
elif page == "7. Report":
    md = api("GET", "/report/export")
    with st.container(border=True):
        st.markdown("**Document preview**")
        st.markdown(md)
    st.download_button("⬇️ Download Markdown", md, file_name="tara_report.md")
    with st.expander("Audit trail (who decided what, when)"):
        st.dataframe(api("GET", "/review/audit"), use_container_width=True, hide_index=True)

# ------------------------------------------------------- Knowledge Base ---
elif page == "Knowledge Base":
    st.caption("Approved threat patterns backing every AI suggestion. Citations resolve to these IDs.")
    lib = json.loads(Path(st.session_state.get("lib_path",
        str(Path(__file__).resolve().parents[2] / "Input_Data" / "threat_library.json"))).read_text(encoding="utf-8"))
    q = st.text_input("Search", placeholder="e.g. spoofing OTA")
    cats = ["All"] + sorted({r.get("stride_category", "") for r in lib})
    cat = st.selectbox("STRIDE category", cats)
    hits = [r for r in lib
            if (cat == "All" or r.get("stride_category") == cat)
            and (not q or q.lower() in json.dumps(r).lower())]
    st.caption(f"{len(hits)} of {len(lib)} records")
    st.dataframe([{"id": r["id"], "title": r.get("title", ""), "stride": r.get("stride_category", ""),
                   "ref": r.get("un_r155_reference", "")} for r in hits],
                 use_container_width=True, hide_index=True)
    if hits:
        sel = st.selectbox("Record detail", [r["id"] for r in hits])
        rec = next(r for r in hits if r["id"] == sel)
        with st.container(border=True):
            st.markdown(f"**{rec.get('title', sel)}** `{sel}`")
            st.write(rec.get("description", ""))
            st.markdown(f"**Reference:** `{rec.get('un_r155_reference', '—')}`")
            life = mapping_status(rec)
            badge = ('<span class="pill" style="background:#dc2626">stale — re-validate</span>'
                     if life["stale"] else
                     '<span class="pill" style="background:#16a34a">fresh</span>')
            st.markdown(f"**Mapping:** owner `{life['owner']}`, reviewed `{life['review_date']}` &nbsp; {badge}",
                        unsafe_allow_html=True)
            st.markdown("**Typical assets (mapped by us):** " +
                        ", ".join(f"`{a}`" for a in rec.get("typical_assets", [])))
            for m in rec.get("standard_mitigations", []):
                st.markdown(f"- {m}")

# ------------------------------------------------------------ Settings ---
elif page == "Settings":
    cfg = api("GET", "/config")
    with st.container(border=True):
        st.markdown("**Provider & models** (secrets live in `Model_Prompts_Config/.env`, never shown here)")
        st.dataframe([{"setting": k, "value": v} for k, v in cfg.items()],
                     use_container_width=True, hide_index=True)
    with st.container(border=True):
        st.markdown("**Switching providers is config-only:** set `LLM_PROVIDER` to "
                    "`mock | gemini | groq | openrouter | nvidia` and add that provider's "
                    "`*_API_KEY` to `.env`. No code changes needed.")
