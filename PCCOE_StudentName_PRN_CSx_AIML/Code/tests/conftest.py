"""Isolate tests: temp SQLite/Chroma paths set before any app module imports."""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="tara_test_")
os.environ["SQLITE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CHROMA_DIR"] = f"{_tmp}/chroma"
