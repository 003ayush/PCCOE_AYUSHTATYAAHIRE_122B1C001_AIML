"""API: health, config, validation errors, suggest flow, review, report."""

import json

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app

client = TestClient(app)
ARCH = {
    "components": [{"id": "C-1", "name": "Modem", "description": "cellular", "trust_boundary": "External Facing"}],
    "interfaces": [{"id": "I-1", "name": "OTA", "source": "Cloud (External)", "destination": "C-1",
                    "protocol": "TLS", "description": "updates"}],
}


def test_health_and_config():
    """Liveness probe and non-secret config (client name, model, no keys leaked)."""
    assert client.get("/health").json()["status"] == "ok"
    cfg = client.get("/config").json()
    assert cfg["active_client"] and cfg["active_model"] is not None
    assert "api_key" not in json.dumps(cfg).lower()
    assert "gsk_" not in json.dumps(cfg)


def test_architecture_validate_and_reject():
    """Good JSON validates; broken JSON is a 422 with a message."""
    ok = client.post("/architecture/validate", json={"content": json.dumps(ARCH), "format": "json"})
    assert ok.status_code == 200 and len(ok.json()["components"]) == 1
    bad = client.post("/architecture/validate", json={"content": "{nope", "format": "json"})
    assert bad.status_code == 422


def test_ui_suggest_paths_match_api():
    """The UI's SUGGEST_PATHS must all exist — a wrong path is a silent 404 button."""
    import ast
    from pathlib import Path

    ui_src = (Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    assign = next(n for n in ast.walk(ast.parse(ui_src))
                  if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SUGGEST_PATHS")
    paths = ast.literal_eval(assign.value)
    assert set(paths) == {"asset", "threat", "risk", "mitigation"}
    live = client.get("/openapi.json").json()["paths"]
    for item_type, path in paths.items():
        assert path in live, f"UI calls {path} ({item_type}) but the API has no such route"


def test_suggest_lists_review_and_report_flow():
    """Mock suggest persists nothing but lists work; review 404s cleanly; report renders."""
    init_db()
    assert client.post("/assets/suggest", json={"architecture": ARCH}).status_code == 200
    assert client.get("/assets").status_code == 200
    surface = client.post("/assets/attack-surface", json={"architecture": ARCH}).json()
    assert [e["interface"]["id"] for e in surface] == ["I-1"]
    missing = client.post("/review/asset/NOPE",
                          json={"decision": "approve", "reviewer": "r"})
    assert missing.status_code == 404
    trace = client.get("/report/traceability").json()
    assert "links" in trace and "gaps" in trace
    export = client.get("/report/export")
    assert export.status_code == 200 and "Traceability" in export.text
