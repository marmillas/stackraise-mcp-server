"""Poetry management tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.tools.subprocess_helper import run_command

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    cwd = settings.project_root

    @server.tool(name="poetry_install", description="Run poetry install.")
    def poetry_install() -> dict[str, Any]:
        return run_command(["poetry", "install"], cwd=cwd)

    @server.tool(
        name="poetry_show",
        description="Show installed dependencies (poetry show).",
    )
    def poetry_show() -> dict[str, Any]:
        return run_command(["poetry", "show"], cwd=cwd)
