"""Tests for tool registry."""

from unittest.mock import MagicMock

from abstract_backend_mcp.core.registry import register_all_tools
from abstract_backend_mcp.core.settings import MCPSettings


def test_register_health_always():
    server = MagicMock()
    settings = MCPSettings(
        _env_file=None,
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=False,
        enable_mongodb_tools=False,
        enable_stackraise_tools=False,
    )
    groups = register_all_tools(server, settings)
    assert "health" in groups
    assert "test" not in groups
    assert "fastapi" not in groups


def test_register_all_groups():
    server = MagicMock()
    settings = MCPSettings(
        _env_file=None,
        enable_test_tools=True,
        enable_quality_tools=True,
        enable_fastapi_tools=True,
        enable_mongodb_tools=True,
        enable_stackraise_tools=True,
    )
    groups = register_all_tools(server, settings)
    assert set(groups) == {"health", "test", "quality", "fastapi", "mongodb", "stackraise"}
