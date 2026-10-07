"""Layered architecture diagram as dependency-free SVG.

Components are grouped into columns by trust boundary (external first);
endpoints that are not components (cloud, tester, …) become dashed nodes.
Edge colour encodes the interface class: red = external, purple =
diagnostic/service, green = vehicle-internal. Pure function of Architecture,
no Streamlit import, so tests can assert on the output.
"""

from __future__ import annotations

import html

from app.schemas import Architecture

# Column order for known boundaries; unknown ones append alphabetically after.
BOUNDARY_ORDER = ["External Facing", "Secure Enclave", "Internal TCU Core", "Internal Vehicle Network"]

BOUNDARY_STYLE = {
    "External Facing": ("#fee2e2", "#ef4444"),
    "Secure Enclave": ("#ede9fe", "#8b5cf6"),
    "Internal TCU Core": ("#dbeafe", "#3b82f6"),
    "Internal Vehicle Network": ("#dcfce7", "#22c55e"),
}
DEFAULT_STYLE = ("#f1f5f9", "#6478b")

NODE_W, NODE_H = 168, 56
COL_GAP, ROW_GAP, PAD = 96, 20, 16
LEGEND_H = 26


def _edge_class(source: str, dest: str, protocol: str, external: set[str]) -> str:
    """Classify an interface for colouring: diagnostic > external > internal."""
    blob = f"{source} {dest} {protocol}".lower()
    if any(k in blob for k in ("uds", "jtag", "diagnostic", "tester", "workshop", "uart")):
        return "diagnostic"
    if source in external or dest in external or "external" in blob:
        return "external"
    return "internal"


EDGE_COLOR = {"external": "#ef4444", "diagnostic": "#8b5cf6", "internal": "#22c55e"}


def render_architecture_svg(architecture: Architecture) -> str:
    """Lay out components by trust boundary and return an SVG string."""
    boundaries = sorted({c.trust_boundary for c in architecture.components},
                        key=lambda b: (BOUNDARY_ORDER.index(b) if b in BOUNDARY_ORDER else 99, b))
    cols: dict[str, list] = {b: [] for b in boundaries}
    for comp in architecture.components:
        cols[comp.trust_boundary].append(comp)

    by_id = {c.id: c for c in architecture.components}
    by_name = {c.name: c for c in architecture.components}
    external_endpoints: dict[str, str] = {}  # label -> column (always External Facing)

    def node_key(endpoint: str) -> str:
        """Resolve an endpoint to a component id, or register an external node."""
        if endpoint in by_id or endpoint in by_name:
            comp = by_id.get(endpoint) or by_name[endpoint]
            return f"comp:{comp.id}"
        return f"ext:{external_endpoints.setdefault(endpoint, endpoint)}"

    # Layout: one column per boundary; external endpoints share the first column.
    positions: dict[str, tuple[float, float]] = {}
    for ci, b in enumerate(boundaries):
        x = PAD + ci * (NODE_W + COL_GAP)
        for i, comp in enumerate(cols[b]):
            positions[f"comp:{comp.id}"] = (x, PAD + i * (NODE_H + ROW_GAP))
    ext_keys = [k for k in {node_key(i.source) for i in architecture.interfaces}
                | {node_key(i.destination) for i in architecture.interfaces} if k.startswith("ext:")]
    if ext_keys and boundaries:
        x = PAD  # external endpoints live in the first (external) column, below components
        base = PAD + max((len(cols[b]) for b in boundaries), default=0) * (NODE_H + ROW_GAP) + ROW_GAP
        for i, key in enumerate(sorted(ext_keys)):
            positions[key] = (x, base + i * (NODE_H + ROW_GAP))

    def node_center(key: str) -> tuple[float, float]:
        """Centre of a node box."""
        x, y = positions[key]
        return x + NODE_W / 2, y + NODE_H / 2

    external_names = {c.id for c in architecture.components if c.trust_boundary == "External Facing"}
    parts = []
    width = PAD * 2 + len(boundaries) * NODE_W + (len(boundaries) - 1) * COL_GAP
    height = max((y for _, y in positions.values()), default=PAD) + NODE_H + PAD + LEGEND_H

    # Edges under nodes.
    for iface in architecture.interfaces:
        src, dst = node_key(iface.source), node_key(iface.destination)
        if src not in positions or dst not in positions:
            continue
        x1, y1 = node_center(src)
        x2, y2 = node_center(dst)
        cls = _edge_class(iface.source, iface.destination, iface.protocol, external_names)
        color = EDGE_COLOR[cls]
        if abs(x1 - x2) < 1:  # same column: loop out to the right
            mx = x1 + NODE_W / 2 + 34
            d = f"M {x1 + NODE_W / 2} {y1} C {mx} {y1}, {mx} {y2}, {x2 + NODE_W / 2} {y2}"
        else:
            x1e = x1 + NODE_W / 2 if x2 > x1 else x1 - NODE_W / 2
            x2e = x2 - NODE_W / 2 if x2 > x1 else x2 + NODE_W / 2
            mx = (x1e + x2e) / 2
            d = f"M {x1e} {y1} C {mx} {y1}, {mx} {y2}, {x2e} {y2}"
        label = html.escape(iface.protocol)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>'
            f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 5}" font-size="10" fill="#475569" '
            f'text-anchor="middle">{label}</text>')

    # Nodes over edges.
    for key, (x, y) in positions.items():
        if key.startswith("ext:"):
            label = html.escape(key[4:])
            parts.append(
                f'<ellipse cx="{x + NODE_W / 2}" cy="{y + NODE_H / 2}" rx="{NODE_W / 2}" ry="{NODE_H / 2}" '
                f'fill="#f8fafc" stroke="#94a3b8" stroke-dasharray="6 4" stroke-width="1.5"/>'
                f'<text x="{x + NODE_W / 2}" y="{y + NODE_H / 2 + 4}" font-size="11" fill="#475569" '
                f'text-anchor="middle">{label[:24]}</text>')
        else:
            comp = by_id[key[5:]]
            fill, border = BOUNDARY_STYLE.get(comp.trust_boundary, DEFAULT_STYLE)
            name = html.escape(comp.name)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="8" '
                f'fill="{fill}" stroke="{border}" stroke-width="2"/>'
                f'<text x="{x + NODE_W / 2}" y="{y + 24}" font-size="12" font-weight="600" '
                f'fill="#0f172a" text-anchor="middle">{name[:22]}</text>'
                f'<text x="{x + NODE_W / 2}" y="{y + 41}" font-size="10" fill="#475569" '
                f'text-anchor="middle">{html.escape(comp.id)}</text>')

    # Column headers + legend.
    for ci, b in enumerate(boundaries):
        x = PAD + ci * (NODE_W + COL_GAP)
        _, border = BOUNDARY_STYLE.get(b, DEFAULT_STYLE)
        parts.append(f'<text x="{x}" y="{PAD - 4}" font-size="11" font-weight="700" fill="{border}">'
                     f'{html.escape(b)}</text>')
    ly = height - 8
    legend = (f'<line x1="{PAD}" y1="{ly}" x2="{PAD + 24}" y2="{ly}" stroke="#ef4444" stroke-width="2"/>'
              f'<text x="{PAD + 30}" y="{ly + 4}" font-size="10" fill="#475569">External</text>'
              f'<line x1="{PAD + 110}" y1="{ly}" x2="{PAD + 134}" y2="{ly}" stroke="#22c55e" stroke-width="2"/>'
              f'<text x="{PAD + 140}" y="{ly + 4}" font-size="10" fill="#475569">Vehicle internal</text>'
              f'<line x1="{PAD + 250}" y1="{ly}" x2="{PAD + 274}" y2="{ly}" stroke="#8b5cf6" stroke-width="2"/>'
              f'<text x="{PAD + 280}" y="{ly + 4}" font-size="10" fill="#475569">Diagnostic/service</text>')
    parts.append(legend)

    inner = "\n".join(parts)
    return (
        f'<svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
        f'<path d="M0,0 L7,3 L0,6" fill="none" stroke="#64748b" stroke-width="1.2"/></marker></defs>'
        f"{inner}</svg>")
