"""Deterministic offline LLM for tests and frame-phase runs.

Returns a small, valid JSON envelope so the rest of the pipeline
(schema validation, citation checks, UI) can be exercised without keys.
"""

from __future__ import annotations

import json


class MockLLMClient:
    """Always succeeds with a placeholder, clearly labelled payload."""

    name = "mock"

    def complete(self, prompt: str, system: str = "") -> str:
        """Echo a placeholder JSON object; ignores the prompt content."""
        return json.dumps(
            {
                "items": [],
                "note": "PLACEHOLDER: mock LLM output (no provider configured)",
                "prompt_chars": len(prompt),
            }
        )
