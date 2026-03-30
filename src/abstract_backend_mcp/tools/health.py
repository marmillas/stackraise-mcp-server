"""Health and diagnostic tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    @server.tool(name="ping", description="Check if the MCP server is alive.")
    def ping() -> dict[str, Any]:
        return {"status": "ok", "project": settings.project_name}

    @server.tool(
        name="show_runtime_config",
        description="Show the effective (sanitized) runtime configuration.",
    )
    def show_runtime_config() -> dict[str, Any]:
        return settings.sanitized_dict()

    @server.tool(
        name="list_enabled_tools",
        description="List which tool groups are currently enabled.",
    )
    def list_enabled_tools() -> dict[str, Any]:
        return {
            "health": True,
            "test": settings.enable_test_tools,
            "quality": settings.enable_quality_tools,
            "fastapi": settings.enable_fastapi_tools,
            "mongodb": settings.enable_mongodb_tools,
            "stackraise": settings.enable_stackraise_tools,
        }

    @server.tool(
        name="check_project_health",
        description="Validate project setup: Poetry, FastAPI, Stackraise, MongoDB presence.",
    )
    def check_project_health() -> dict[str, Any]:
        from abstract_backend_mcp.bootstrap.detect_project import detect_project

        return detect_project(settings.project_root)

    @server.tool(
        name="show_project_instructions",
        description="Show the parsed PROJECT.md instructions and metadata.",
    )
    def show_project_instructions() -> dict[str, Any]:
        from abstract_backend_mcp.core.instructions import load_project_instructions

        pi = load_project_instructions(
            settings.project_root,
            settings.project_instructions_file,
        )
        return pi.model_dump()
