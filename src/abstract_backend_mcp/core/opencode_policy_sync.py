"""Synchronization helpers for local opencode agent prompts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from abstract_backend_mcp.bootstrap.init_project import render_opencode_content
from abstract_backend_mcp.core.agent_prompt_layers import apply_agent_prompt_layers

AGENT_ROLES: tuple[str, ...] = ("audit", "build", "fix", "doc", "plan")


def _prompt_regex_for_role(role: str) -> re.Pattern[str]:
    return re.compile(
        rf'("{role}"\s*:\s*\{{.*?"prompt"\s*:\s*)("(?:\\.|[^"\\])*")(\s*,\s*"tools")',
        re.S,
    )


@dataclass
class OpencodePolicySyncResult:
    """Result payload for opencode policy sync operation."""

    path: str
    created: bool
    updated: bool
    updated_roles: list[str]
    message: str


class OpencodePolicySyncError(RuntimeError):
    """Raised when local opencode policy cannot be synchronized."""


def _replace_role_prompt(raw_text: str, role: str) -> tuple[str, bool]:
    pattern = _prompt_regex_for_role(role)
    match = pattern.search(raw_text)
    if not match:
        return raw_text, False

    prefix, quoted_prompt, suffix = match.groups()
    try:
        current_prompt = json.loads(quoted_prompt)
    except json.JSONDecodeError as exc:
        raise OpencodePolicySyncError(
            f"agent.{role}.prompt is not a valid JSON string"
        ) from exc

    synchronized_prompt = apply_agent_prompt_layers(role, current_prompt)
    if synchronized_prompt == current_prompt:
        return raw_text, False

    replacement = f"{prefix}{json.dumps(synchronized_prompt)}{suffix}"
    updated = raw_text[: match.start()] + replacement + raw_text[match.end() :]
    return updated, True


def sync_opencode_agent_policy(
    opencode_path: Path,
    *,
    create_if_missing: bool = True,
) -> OpencodePolicySyncResult:
    """Ensure local opencode prompts contain current layered agent policies."""
    target = opencode_path.resolve()
    created = False

    if not target.exists():
        if not create_if_missing:
            raise OpencodePolicySyncError(
                f"{target} does not exist. Run 'abstract-mcp init' or enable creation."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_opencode_content(target.parent)
        target.write_text(rendered, encoding="utf-8")
        created = True

    raw = target.read_text(encoding="utf-8")
    updated_roles: list[str] = []
    updated_raw = raw

    for role in AGENT_ROLES:
        updated_raw, role_updated = _replace_role_prompt(updated_raw, role)
        if role_updated:
            updated_roles.append(role)

    if not updated_roles:
        if created:
            return OpencodePolicySyncResult(
                path=str(target),
                created=True,
                updated=True,
                updated_roles=[],
                message="Created opencode.jsonc with synchronized agent collaboration policies.",
            )
        return OpencodePolicySyncResult(
            path=str(target),
            created=False,
            updated=False,
            updated_roles=[],
            message="opencode.jsonc agent policies already up to date.",
        )

    target.write_text(updated_raw, encoding="utf-8")
    return OpencodePolicySyncResult(
        path=str(target),
        created=created,
        updated=True,
        updated_roles=updated_roles,
        message=(
            "Created and synchronized opencode.jsonc agent policies."
            if created
            else "Synchronized opencode.jsonc agent policies."
        ),
    )
