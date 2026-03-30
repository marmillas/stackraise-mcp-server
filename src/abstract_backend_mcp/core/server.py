"""MCP server factory."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from abstract_backend_mcp.core.instructions import load_project_instructions
from abstract_backend_mcp.core.logging import get_logger
from abstract_backend_mcp.core.registry import register_all_tools
from abstract_backend_mcp.core.settings import MCPSettings

logger = get_logger()


def create_server(settings: MCPSettings | None = None) -> FastMCP:
    """Build and return a configured MCP server ready to run."""
    if settings is None:
        settings = MCPSettings()

    project_instructions = load_project_instructions(
        settings.project_root,
        settings.project_instructions_file,
    )

    server = FastMCP(
        name=f"abstract-mcp ({project_instructions.name or settings.project_name})",
        instructions=project_instructions.build_server_instructions(),
    )

    # Attach settings and instructions to server for tools to access
    server._abmcp_settings = settings  # type: ignore[attr-defined]
    server._abmcp_instructions = project_instructions  # type: ignore[attr-defined]

    groups = register_all_tools(server, settings)
    logger.info(
        "Server '%s' ready – %d tool groups loaded",
        settings.project_name,
        len(groups),
    )
    return server
