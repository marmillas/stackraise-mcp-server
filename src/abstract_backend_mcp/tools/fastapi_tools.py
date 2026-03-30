"""FastAPI introspection tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.adapters.fastapi_adapter import FastAPIAdapter

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    adapter = FastAPIAdapter(settings.fastapi_app_path)

    @server.tool(name="list_routes", description="List all FastAPI routes.")
    def list_routes() -> list[dict[str, Any]]:
        try:
            return adapter.list_routes()
        except Exception as exc:
            return [{"error": str(exc)}]

    @server.tool(
        name="find_route",
        description="Find routes matching a path fragment.",
    )
    def find_route(path_fragment: str) -> list[dict[str, Any]]:
        try:
            return adapter.find_routes(path_fragment)
        except Exception as exc:
            return [{"error": str(exc)}]

    @server.tool(
        name="show_openapi_summary",
        description="Show a summary of the FastAPI OpenAPI schema.",
    )
    def show_openapi_summary() -> dict[str, Any]:
        try:
            return adapter.get_openapi_summary()
        except Exception as exc:
            return {"error": str(exc)}
