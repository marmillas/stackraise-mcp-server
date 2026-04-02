"""Composable prompt layering utilities for agent role prompts."""

from __future__ import annotations

from abstract_backend_mcp.core.build_policy import ensure_builder_checkpoint_policy
from abstract_backend_mcp.core.collaboration_policy import ensure_role_collaboration_policy


def apply_agent_prompt_layers(role: str, base_prompt: str) -> str:
    """Apply additive prompt layers for a specific role.

    Layers are strictly additive and never remove existing base prompt content.
    """
    layered_prompt = base_prompt.rstrip()
    if role == "build":
        layered_prompt = ensure_builder_checkpoint_policy(layered_prompt)
    return ensure_role_collaboration_policy(layered_prompt, role)
