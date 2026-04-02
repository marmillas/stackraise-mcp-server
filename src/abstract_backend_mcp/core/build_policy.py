"""Shared builder policy helpers for checkpoint workflow."""

from __future__ import annotations

from importlib.resources import files

POLICY_MARKER = "## Mandatory checkpoint workflow (before and after implementation)"


def load_builder_checkpoint_policy() -> str:
    """Load canonical checkpoint policy text from versioned template resource."""
    policy = files("abstract_backend_mcp.templates").joinpath("build_checkpoint_policy.txt")
    return policy.read_text(encoding="utf-8").strip()


def ensure_builder_checkpoint_policy(prompt: str) -> str:
    """Append canonical checkpoint policy to builder prompt if missing."""
    policy_text = load_builder_checkpoint_policy()
    normalized_prompt = prompt.rstrip()
    if POLICY_MARKER in normalized_prompt:
        return normalized_prompt
    return f"{normalized_prompt}\n\n{policy_text}"
