"""Tests for additive agent prompt layering."""

from __future__ import annotations

from abstract_backend_mcp.core.agent_prompt_layers import apply_agent_prompt_layers
from abstract_backend_mcp.core.build_policy import POLICY_MARKER
from abstract_backend_mcp.core.collaboration_policy import CONTRACT_MARKER, ROLE_ADDENDUM_MARKERS


def test_all_roles_receive_collaboration_layers_additively() -> None:
    for role in ("audit", "build", "fix", "doc", "plan"):
        base_prompt = f"core prompt for {role}"
        layered = apply_agent_prompt_layers(role, base_prompt)

        assert base_prompt in layered
        assert CONTRACT_MARKER in layered
        assert ROLE_ADDENDUM_MARKERS[role] in layered


def test_prompt_layering_is_idempotent() -> None:
    base_prompt = "core build prompt"
    once = apply_agent_prompt_layers("build", base_prompt)
    twice = apply_agent_prompt_layers("build", once)

    assert once == twice
    assert POLICY_MARKER in twice
