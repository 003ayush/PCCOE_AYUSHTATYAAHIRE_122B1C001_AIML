"""Load threat-library style records from JSON, CSV, or XML files.

Every loader returns a list of plain dicts with at least ``id`` and ``text``
keys (extra fields are kept as metadata). Anything unrecognised raises a
clear ``ValueError`` instead of a stack trace.
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List


def _normalise(record: Dict, source: Path) -> Dict:
    """Ensure required keys exist and build a single searchable ``text`` field."""
    if "id" not in record:
        raise ValueError(f"{source.name}: record missing 'id': {record}")
    text = record.get("text") or " ".join(
        str(v) for k, v in record.items() if isinstance(v, str) and k != "id"
    )
    return {**record, "text": text.strip()}


def load_json(path: Path) -> List[Dict]:
    """Load a JSON array (or ``{items: [...]}`` object) of records."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("items", data.get("threats", [data]))
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a JSON array of records")
    return [_normalise(r, path) for r in data]


def load_csv(path: Path) -> List[Dict]:
    """Load records from a CSV file with a header row."""
    with path.open(newline="", encoding="utf-8") as fh:
        return [_normalise(row, path) for row in csv.DictReader(fh)]


def load_xml(path: Path) -> List[Dict]:
    """Load records: each child element of the root becomes one record.

    Element attributes and child-element text become record fields.
    """
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    records = []
    for el in root:
        record = dict(el.attrib)
        for child in el:
            record[child.tag] = (child.text or "").strip()
        if el.text and el.text.strip():
            record.setdefault("text", el.text.strip())
        if not record:  # leaf element with plain text
            record = {"id": el.attrib.get("id", el.tag), "text": (el.text or "").strip()}
        records.append(_normalise(record, path))
    return records


_LOADERS = {".json": load_json, ".csv": load_csv, ".xml": load_xml}


def load_records(path: str | Path) -> List[Dict]:
    """Dispatch on file extension; supported: .json, .csv, .xml."""
    path = Path(path)
    loader = _LOADERS.get(path.suffix.lower())
    if loader is None:
        raise ValueError(f"Unsupported format '{path.suffix}' for {path.name} (use JSON/XML/CSV)")
    return loader(path)
