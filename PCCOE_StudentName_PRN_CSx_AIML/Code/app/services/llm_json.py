"""Structured LLM calls: JSON parsing with retries and citation flagging."""

from __future__ import annotations

import json
import time
from typing import Any, List

from app.llm.base import LLMClient
from app.schemas import ApprovalStatus, CitationMixin


def _rate_limited(exc: Exception) -> bool:
    """Detect HTTP 429 / rate-limit errors across provider SDKs."""
    return getattr(exc, "status_code", None) == 429 or "rate limit" in str(exc).lower()


def complete_json(client: LLMClient, prompt: str, system: str = "", retries: int = 2):
    """Call the LLM and parse JSON, retrying transient failures with backoff.

    Retries cover both malformed JSON and provider errors (including free-tier
    429s, which wait longer). After exhaustion raises a ValueError naming the
    provider and the likely cause, so routers surface it instead of a bare 500.
    """
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return json.loads(client.complete(prompt, system=system))
        except Exception as exc:  # noqa: BLE001 - every failure mode retries
            last_error = exc
            if attempt < retries:
                time.sleep(5 if _rate_limited(exc) else 1)
    raise ValueError(
        f"LLM '{client.name}' failed after {retries + 1} tries ({last_error}). "
        f"On free tiers this is usually rate limiting — wait a minute and retry."
    )


def items_envelope(parsed: Any) -> List[dict]:
    """Accept a bare list or an {"items": [...]} envelope; anything else is an error."""
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        return parsed["items"]
    raise ValueError(f"Unexpected LLM output shape: {type(parsed).__name__}")


def ensure_drafts_or_raise(final: dict, task: str) -> List[dict]:
    """Surface graph failures to the caller; silent empties hide outages.

    Empty drafts with no errors is a legitimate mock/empty-library result and
    passes through. Errors with no drafts (provider down, rate-limited,
    exhausted budget) become a ValueError that routers report as a 502.
    """
    if not final.get("drafts") and final.get("errors"):
        unique = list(dict.fromkeys(final["errors"]))  # the same bad draft often fails repeatedly
        shown = "; ".join(unique[:3]) + (f"; …and {len(unique) - 3} more" if len(unique) > 3 else "")
        raise ValueError(f"{task} pipeline failed: {shown}")
    return final.get("drafts", [])


def flag_uncited(item: CitationMixin) -> CitationMixin:
    """Mark items with no supporting sources as needing expert review."""
    if not item.source_ids:
        item.status = ApprovalStatus.NEEDS_EXPERT_REVIEW
        item.review_note = "No supporting library source; needs expert review."
    return item
