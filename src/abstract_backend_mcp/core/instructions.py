"""Load project instructions from a PROJECT.md file (frontmatter + markdown)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from abstract_backend_mcp.core.logging import get_logger

logger = get_logger()

_DEFAULT_INSTRUCTIONS = (
    "Backend MCP server providing tools for project inspection, "
    "testing, quality checks, FastAPI introspection, MongoDB operations "
    "and Stackraise context extraction."
)


class ProjectInstructions(BaseModel):
    """Parsed content of a PROJECT.md file."""

    name: str | None = None
    stack: list[str] = Field(default_factory=list)
    conventions: list[str] = Field(default_factory=list)
    description: str = ""
    instructions: str = ""

    def build_server_instructions(self) -> str:
        """Compose the full instructions string for the MCP server."""
        parts: list[str] = []

        if self.description:
            parts.append(f"Project: {self.description}")
        if self.stack:
            parts.append(f"Stack: {', '.join(self.stack)}")
        if self.conventions:
            parts.append("Conventions:\n" + "\n".join(f"- {c}" for c in self.conventions))
        if self.instructions:
            parts.append(self.instructions)

        return "\n\n".join(parts) if parts else _DEFAULT_INSTRUCTIONS


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split a file into YAML frontmatter dict and markdown body."""
    if not content.startswith("---"):
        return {}, content.strip()

    # Find closing ---
    end = content.find("---", 3)
    if end == -1:
        return {}, content.strip()

    fm_raw = content[3:end].strip()
    body = content[end + 3 :].strip()

    try:
        fm = yaml.safe_load(fm_raw)
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError as exc:
        logger.warning("Invalid frontmatter in PROJECT.md: %s", exc)
        fm = {}

    return fm, body


def load_project_instructions(
    project_root: str,
    instructions_file: str = "PROJECT.md",
) -> ProjectInstructions:
    """Load and parse a PROJECT.md (or configured file) from the project root."""
    path = Path(instructions_file)
    if not path.is_absolute():
        path = Path(project_root) / path

    if not path.is_file():
        logger.info("No instructions file at %s — using defaults", path)
        return ProjectInstructions(instructions=_DEFAULT_INSTRUCTIONS)

    content = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(content)

    return ProjectInstructions(
        name=fm.get("name"),
        stack=fm.get("stack", []),
        conventions=fm.get("conventions", []),
        description=fm.get("description", ""),
        instructions=body,
    )
