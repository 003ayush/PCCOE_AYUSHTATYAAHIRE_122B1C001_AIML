"""Application configuration.

Settings are resolved from (highest precedence first):
  1. Process environment variables
  2. ``Model_Prompts_Config/.env`` (loaded if present)
  3. Built-in defaults (offline-friendly: mock LLM provider)

All data locations and provider keys are config-only so swapping in real
data files or a different LLM provider needs no code changes.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Code/app/config.py -> Code -> package root (PCCOE_StudentName_PRN_CSx_AIML)
CODE_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = CODE_DIR.parent
INPUT_DATA_DIR = PACKAGE_ROOT / "Input_Data"
PROMPTS_CONFIG_DIR = PACKAGE_ROOT / "Model_Prompts_Config"

# Load overrides before reading any setting below.
load_dotenv(PROMPTS_CONFIG_DIR / ".env")


def _env(name: str, default: str) -> str:
    """Env value, treating a blank entry (e.g. `KEY=` in .env) as unset."""
    return os.getenv(name, default) or default


class Settings:
    """Runtime settings; every field can be overridden via an env var of the same name (upper-cased)."""

    def __init__(self) -> None:
        """Populate settings from environment variables with safe defaults."""
        self.app_name: str = _env("APP_NAME", "TARA Assistant")
        self.llm_provider: str = _env("LLM_PROVIDER", "mock")
        self.embedding_model: str = _env("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self.input_data_dir: Path = Path(_env("INPUT_DATA_DIR", str(INPUT_DATA_DIR)))
        self.chroma_dir: Path = Path(_env("CHROMA_DIR", str(CODE_DIR / "chroma_db")))
        self.sqlite_url: str = _env("SQLITE_URL", f"sqlite:///{CODE_DIR / 'tara.db'}")
        # OpenAI-compatible endpoint override (used by Groq/OpenRouter/NVIDIA presets).
        self.openai_base_url: str = os.getenv("OPENAI_BASE_URL", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        # Per-provider keys; empty unless the user supplies them. The mock provider needs none.
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
        self.nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
        self.mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
        # Agentic pipeline bounds (PLAN §5a): hard cap on knowledge rounds,
        # optional LLM query rewrite (off by default: deterministic retrieval).
        self.max_knowledge_rounds: int = int(_env("MAX_KNOWLEDGE_ROUNDS", "2"))
        self.knowledge_llm_rewrite: bool = _env("KNOWLEDGE_LLM_REWRITE", "false").lower() == "true"


# Shared settings object imported elsewhere in the app.
settings = Settings()
