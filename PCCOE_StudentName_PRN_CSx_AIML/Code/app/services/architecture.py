"""Parse uploaded architecture descriptions (JSON/XML) into Architecture."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from app.schemas import Architecture


def parse_architecture(content: str, fmt: str) -> Architecture:
    """Validate uploaded content; raise a clear error on bad shape or format."""
    fmt = fmt.lower()
    if fmt == "json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
    elif fmt == "xml":
        data = _xml_to_dict(content)
    else:
        raise ValueError(f"Unsupported architecture format '{fmt}' (use json or xml)")
    try:
        return Architecture.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Architecture validation failed: {exc}") from exc


def _xml_to_dict(content: str) -> dict:
    """Map <component>/<interface> elements (attrs or children) to plain dicts."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc
    out: dict = {"components": [], "interfaces": []}
    for el in root.iter():
        if el.tag not in ("component", "interface"):
            continue
        record = dict(el.attrib)
        for child in el:
            record[child.tag] = (child.text or "").strip()
        out["components" if el.tag == "component" else "interfaces"].append(record)
    return out
