"""Prompt layering helpers for multi-agent collaboration boundaries."""

from __future__ import annotations

from importlib.resources import files

CONTRACT_MARKER = "## Multi-agent collaboration contract"

ROLE_ADDENDUM_FILES = {
    "build": "agent_addendum_build.txt",
    "fix": "agent_addendum_fix.txt",
    "audit": "agent_addendum_audit.txt",
    "doc": "agent_addendum_doc.txt",
    "plan": "agent_addendum_plan.txt",
}

ROLE_ADDENDUM_MARKERS = {
    "build": "### Role boundary addendum (build)",
    "fix": "### Role boundary addendum (fix)",
    "audit": "### Role boundary addendum (audit)",
    "doc": "### Role boundary addendum (doc)",
    "plan": "### Role boundary addendum (plan)",
}


def _load_template_text(file_name: str) -> str:
    resource = files("abstract_backend_mcp.templates").joinpath(file_name)
    return resource.read_text(encoding="utf-8").strip()


def load_collaboration_contract() -> str:
    """Return canonical collaboration contract text shared by all agents."""
    return _load_template_text("agent_collaboration_contract.txt")


def load_role_addendum(role: str) -> str:
    """Return canonical role boundary addendum for a given agent role."""
    if role not in ROLE_ADDENDUM_FILES:
        raise ValueError(f"Unsupported agent role '{role}' for collaboration addendum")
    return _load_template_text(ROLE_ADDENDUM_FILES[role])


def ensure_role_collaboration_policy(prompt: str, role: str) -> str:
    """Append collaboration contract and role addendum if missing."""
    if role not in ROLE_ADDENDUM_MARKERS:
        raise ValueError(f"Unsupported agent role '{role}' for collaboration policy")

    normalized_prompt = prompt.rstrip()
    if CONTRACT_MARKER not in normalized_prompt:
        normalized_prompt = f"{normalized_prompt}\n\n{load_collaboration_contract()}"

    role_marker = ROLE_ADDENDUM_MARKERS[role]
    if role_marker not in normalized_prompt:
        normalized_prompt = f"{normalized_prompt}\n\n{load_role_addendum(role)}"

    return normalized_prompt
