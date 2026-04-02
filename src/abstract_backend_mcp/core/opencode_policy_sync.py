"""Synchronization helpers for local opencode build policy."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from abstract_backend_mcp.bootstrap.init_project import render_opencode_content
from abstract_backend_mcp.core.build_policy import ensure_builder_checkpoint_policy

_BUILD_PROMPT_RE = re.compile(
    r'("build"\s*:\s*\{.*?"prompt"\s*:\s*)("(?:\\.|[^"\\])*")(\s*,\s*"tools")',
    re.S,
)


@dataclass
class OpencodePolicySyncResult:
    """Result payload for opencode policy sync operation."""

    path: str
    created: bool
    updated: bool
    message: str


class OpencodePolicySyncError(RuntimeError):
    """Raised when local opencode policy cannot be synchronized."""


def sync_opencode_build_policy(
    opencode_path: Path,
    *,
    create_if_missing: bool = True,
) -> OpencodePolicySyncResult:
    """Ensure local opencode build prompt contains checkpoint policy text."""
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
    match = _BUILD_PROMPT_RE.search(raw)
    if not match:
        raise OpencodePolicySyncError(
            "Could not locate agent.build.prompt in opencode.jsonc. "
            "Please ensure the file follows generated structure."
        )

    prefix, quoted_prompt, suffix = match.groups()
    try:
        current_prompt = json.loads(quoted_prompt)
    except json.JSONDecodeError as exc:
        raise OpencodePolicySyncError("agent.build.prompt is not a valid JSON string") from exc

    synchronized_prompt = ensure_builder_checkpoint_policy(current_prompt)
    if synchronized_prompt == current_prompt:
        if created:
            return OpencodePolicySyncResult(
                path=str(target),
                created=True,
                updated=True,
                message="Created opencode.jsonc with synchronized checkpoint policy.",
            )
        return OpencodePolicySyncResult(
            path=str(target),
            created=False,
            updated=False,
            message="opencode.jsonc build policy already up to date.",
        )

    replacement = f"{prefix}{json.dumps(synchronized_prompt)}{suffix}"
    updated_raw = raw[: match.start()] + replacement + raw[match.end() :]
    target.write_text(updated_raw, encoding="utf-8")
    return OpencodePolicySyncResult(
        path=str(target),
        created=created,
        updated=True,
        message=(
            "Created and synchronized opencode.jsonc build policy."
            if created
            else "Synchronized opencode.jsonc build policy."
        ),
    )
