"""OpenAI-compatible client presets for free/hosted providers.

The ``openai`` package is imported lazily so the mock provider and tests
work without it installed.
"""

from __future__ import annotations

import os

from app.config import settings

# provider name -> (base_url, default model)
PROVIDER_PRESETS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash"),
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "meta/llama-3.3-70b-instruct"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
}


class OpenAICompatibleClient:
    """One client implementation usable for every OpenAI-compatible endpoint."""

    def __init__(self, name: str, base_url: str, api_key: str, model: str) -> None:
        """Store connection details; the SDK client is created on first use."""
        self.name = name
        self.model = model
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        """Lazily construct the OpenAI client so importing this module stays cheap."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(base_url=self._base_url, api_key=self._api_key, timeout=900.0)
        return self._client

    def complete(self, prompt: str, system: str = "") -> str:
        """Send the prompt to the configured endpoint and return text content."""
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        resp = self._get_client().chat.completions.create(model=self._model, messages=messages)
        return resp.choices[0].message.content or ""


def build_provider(name: str) -> OpenAICompatibleClient | None:
    """Create a client for a preset provider, or None if its key is missing.

    The model is overridable per provider, e.g. ``GROQ_MODEL=llama-3.1-8b-instant``
    for the roomier free-tier allowance.
    """
    if name not in PROVIDER_PRESETS:
        raise ValueError(f"Unknown provider: {name}")
    api_key = getattr(settings, f"{name}_api_key", "")
    if not api_key:
        return None
    base_url, default_model = PROVIDER_PRESETS[name]
    if settings.openai_base_url:  # explicit override beats the preset URL
        base_url = settings.openai_base_url
    return OpenAICompatibleClient(name, base_url, api_key,
                                  os.getenv(f"{name.upper()}_MODEL", default_model))
