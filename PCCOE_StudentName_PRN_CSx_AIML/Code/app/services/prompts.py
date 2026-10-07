"""Load and render versioned prompt templates from Model_Prompts_Config/.

Templates use ``$variable`` substitution (string.Template) so JSON examples
in prompts with literal braces never clash with the placeholder syntax.
"""

from __future__ import annotations

import re
from string import Template

from app.config import PROMPTS_CONFIG_DIR


def load_prompt(name: str, version: int = 1) -> tuple[int, str, str]:
    """Read ``{name}.v{version}.md``; return (version, system, user_template)."""
    path = PROMPTS_CONFIG_DIR / f"{name}.v{version}.md"
    text = path.read_text(encoding="utf-8")
    header = re.search(r"^# version:\s*(\d+)", text, re.MULTILINE)
    system = re.search(r"## SYSTEM\s*\n(.*?)(?=\n## USER|\Z)", text, re.DOTALL)
    user = re.search(r"## USER\s*\n(.*)", text, re.DOTALL)
    if not (header and system and user):
        raise ValueError(f"Malformed prompt template: {path.name}")
    return int(header.group(1)), system.group(1).strip(), user.group(1).strip()


def render(template: str, **variables) -> str:
    """Substitute ``$variables`` into a user template."""
    return Template(template).substitute(variables)
