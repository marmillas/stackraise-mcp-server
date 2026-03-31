"""FastAPI introspection tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.adapters.fastapi_adapter import FastAPIAdapter
from abstract_backend_mcp.tools.response_helper import build_error_payload, build_success_payload

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    adapter = FastAPIAdapter(settings.fastapi_app_path)

    def error_payload(
        *,
        code: str,
        message: str,
        retriable: bool,
        blocked: bool = False,
    ) -> dict[str, Any]:
        return build_error_payload(
            code=code,
            message=message,
            retriable=retriable,
            blocked=blocked,
        )

    def assert_runtime_imports_allowed() -> dict[str, Any] | None:
        if settings.allow_fastapi_runtime_imports:
            return None
        return error_payload(
            code="FASTAPI_RUNTIME_IMPORTS_BLOCKED",
            message=(
                "FastAPI runtime imports are disabled. "
                "Set ALLOW_FASTAPI_RUNTIME_IMPORTS=true to enable."
            ),
            retriable=False,
            blocked=True,
        )

    @server.tool(name="list_routes", description="List all FastAPI routes.")
    def list_routes() -> dict[str, Any]:
        blocked = assert_runtime_imports_allowed()
        if blocked is not None:
            return blocked

        try:
            routes = adapter.list_routes()
            return build_success_payload(items=routes, total=len(routes))
        except Exception as exc:
            return error_payload(
                code="FASTAPI_LIST_ROUTES_FAILED",
                message=str(exc),
                retriable=True,
            )

    @server.tool(
        name="find_route",
        description="Find routes matching a path fragment.",
    )
    def find_route(path_fragment: str) -> dict[str, Any]:
        blocked = assert_runtime_imports_allowed()
        if blocked is not None:
            return blocked

        try:
            routes = adapter.find_routes(path_fragment)
            return build_success_payload(
                items=routes,
                total=len(routes),
                path_fragment=path_fragment,
            )
        except Exception as exc:
            return error_payload(
                code="FASTAPI_FIND_ROUTE_FAILED",
                message=str(exc),
                retriable=True,
            )

    @server.tool(
        name="show_openapi_summary",
        description="Show a summary of the FastAPI OpenAPI schema.",
    )
    def show_openapi_summary() -> dict[str, Any]:
        blocked = assert_runtime_imports_allowed()
        if blocked is not None:
            return blocked

        try:
            summary = adapter.get_openapi_summary()
            return build_success_payload(summary=summary)
        except Exception as exc:
            return error_payload(
                code="FASTAPI_OPENAPI_SUMMARY_FAILED",
                message=str(exc),
                retriable=True,
            )
