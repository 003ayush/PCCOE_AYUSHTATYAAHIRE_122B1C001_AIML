"""LLM layer: mock output shape, fallback chain, factory default."""

import json

import pytest

from app.llm import get_llm_client
from app.llm.fallback import FallbackChain
from app.llm.mock import MockLLMClient


class _Boom:
    """Client that always fails, to exercise the fallback."""

    name = "boom"

    def complete(self, prompt: str, system: str = "") -> str:
        raise RuntimeError("provider down")


def test_mock_returns_items_envelope():
    """Mock output parses as JSON with an items list."""
    parsed = json.loads(MockLLMClient().complete("hello"))
    assert isinstance(parsed["items"], list)


def test_fallback_skips_failures():
    """Chain returns the first success after a failing provider."""
    out = FallbackChain([_Boom(), MockLLMClient()]).complete("x")
    assert "items" in json.loads(out)


class _Flaky:
    """Fails like a rate-limited provider twice, then returns valid JSON."""

    name = "flaky"

    def __init__(self):
        self.calls = 0

    def complete(self, prompt: str, system: str = "") -> str:
        self.calls += 1
        if self.calls < 3:
            err = RuntimeError("429 rate limit exceeded, try again")
            err.status_code = 429
            raise err
        return json.dumps({"items": []})


class _Down:
    """Always fails transport-level, like a dead endpoint."""

    name = "down"

    def complete(self, prompt: str, system: str = "") -> str:
        raise ConnectionError("connection refused")


def test_complete_json_retries_rate_limit_then_succeeds(monkeypatch):
    """429s back off and retry instead of failing the whole action."""
    import app.services.llm_json as llm_json

    monkeypatch.setattr(llm_json.time, "sleep", lambda s: None)
    flaky = _Flaky()
    assert llm_json.complete_json(flaky, "hi") == {"items": []}
    assert flaky.calls == 3


def test_complete_json_gives_actionable_error(monkeypatch):
    """Persistent outage becomes a named, hint-carrying ValueError (routers -> 502)."""
    import app.services.llm_json as llm_json

    monkeypatch.setattr(llm_json.time, "sleep", lambda s: None)
    with pytest.raises(ValueError, match="down.*rate limiting"):
        llm_json.complete_json(_Down(), "hi", retries=1)


def test_suggest_raises_on_errors_without_drafts():
    """Provider down + empty library must error loudly, never silently empty."""
    from app.services.threats import suggest_threats
    from tests.test_agents import _FakeStore

    with pytest.raises(ValueError, match="threat pipeline failed"):
        suggest_threats(_Down(), _FakeStore([]), [], [])

def test_fallback_empty_chain_rejected():
    """A chain with no clients is a configuration error."""
    with pytest.raises(ValueError):
        FallbackChain([])


def test_factory_defaults_to_mock_without_keys(monkeypatch):
    """No provider configured -> offline mock client (keys/env-independent)."""
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "mock")
    assert get_llm_client().name == "mock"
