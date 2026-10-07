"""Config: blank .env entries fall back to defaults; blank keys stay unused."""

from app.config import CODE_DIR, Settings, _env
from app.llm.providers import build_provider


def test_blank_entries_fall_back_to_defaults(monkeypatch):
    """A copied template with empty values must behave as if unset."""
    monkeypatch.setenv("SQLITE_URL", "")
    monkeypatch.setenv("CHROMA_DIR", "")
    monkeypatch.setenv("INPUT_DATA_DIR", "")
    monkeypatch.setenv("MAX_KNOWLEDGE_ROUNDS", "")
    s = Settings()
    assert s.sqlite_url == f"sqlite:///{CODE_DIR / 'tara.db'}"
    assert str(s.chroma_dir).endswith("chroma_db")
    assert s.max_knowledge_rounds == 2
    assert _env("SQLITE_URL", "dflt") == "dflt"


def test_blank_key_stays_unused(monkeypatch):
    """A blanked-out key on a fresh Settings must not look configured."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert Settings().gemini_api_key == ""


def test_template_has_no_placeholder_keys():
    """The committed template must not contain look-like-a-key junk values."""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "Model_Prompts_Config" / ".env.example").read_text()
    for line in text.splitlines():
        if line.strip().startswith(("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
                                    "OPENAI_API_KEY")):
            assert line.split("=", 1)[1].strip() == "", f"placeholder key in template: {line}"
