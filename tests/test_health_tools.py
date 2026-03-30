"""Tests for health tools."""

from abstract_backend_mcp.core.server import create_server
from abstract_backend_mcp.core.settings import MCPSettings


def test_server_creates_without_error():
    settings = MCPSettings(
        _env_file=None,
        enable_fastapi_tools=False,
        enable_mongodb_tools=False,
        enable_stackraise_tools=False,
    )
    server = create_server(settings)
    assert server is not None
    assert settings.project_name in server.name
