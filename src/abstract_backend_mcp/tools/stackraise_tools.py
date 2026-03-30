"""Stackraise introspection and context tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    adapter = StackraiseAdapter(settings.stackraise_package_name)

    @server.tool(
        name="detect_stackraise",
        description="Check whether Stackraise is installed and importable.",
    )
    def detect_stackraise() -> dict[str, Any]:
        return {
            "available": adapter.is_available(),
            "package": settings.stackraise_package_name,
        }

    @server.tool(
        name="show_stackraise_modules",
        description="List which Stackraise sub-modules are available.",
    )
    def show_stackraise_modules() -> dict[str, Any]:
        if not adapter.is_available():
            return {"available": False, "modules": {}}
        return {"available": True, "modules": adapter.detect_modules()}

    @server.tool(
        name="show_stackraise_db_metadata",
        description="Show Stackraise database/document metadata.",
    )
    def show_stackraise_db_metadata() -> dict[str, Any]:
        return adapter.get_db_metadata()

    @server.tool(
        name="show_stackraise_logging_metadata",
        description="Show Stackraise logging configuration.",
    )
    def show_stackraise_logging_metadata() -> dict[str, Any]:
        return adapter.get_logging_metadata()

    @server.tool(
        name="show_stackraise_di_metadata",
        description="Show Stackraise dependency-injection metadata.",
    )
    def show_stackraise_di_metadata() -> dict[str, Any]:
        return adapter.get_di_metadata()

    @server.tool(
        name="show_stackraise_auth_scopes",
        description="Show Stackraise auth scopes and guards.",
    )
    def show_stackraise_auth_scopes() -> dict[str, Any]:
        return adapter.get_auth_metadata()

    @server.tool(
        name="list_stackraise_crud_resources",
        description="List detected CRUD resources.",
    )
    def list_stackraise_crud_resources() -> list[dict[str, Any]]:
        return adapter.list_crud_resources()

    @server.tool(
        name="list_stackraise_workflows",
        description="Detect workflow modules (RPA, email, templating).",
    )
    def list_stackraise_workflows() -> dict[str, Any]:
        return adapter.get_workflow_map()

    @server.tool(
        name="show_stackraise_frontend_contracts",
        description="Detect frontend contract libraries.",
    )
    def show_stackraise_frontend_contracts() -> dict[str, Any]:
        return adapter.get_frontend_contracts()

    @server.tool(
        name="build_stackraise_context_snapshot",
        description="Build a full Stackraise context snapshot (static/runtime/hybrid).",
    )
    def build_stackraise_context_snapshot(mode: str = "") -> dict[str, Any]:
        effective_mode = mode or settings.stackraise_context_mode.value
        try:
            from abstract_backend_mcp.context.normalizer import build_snapshot

            return build_snapshot(settings, adapter, mode=effective_mode)
        except Exception as exc:
            return {
                "error": str(exc),
                "mode": effective_mode,
                "partial": True,
            }

    @server.tool(
        name="show_stackraise_context_warnings",
        description="Show warnings about incomplete context extraction.",
    )
    def show_stackraise_context_warnings() -> dict[str, Any]:
        try:
            from abstract_backend_mcp.context.normalizer import build_snapshot

            snapshot = build_snapshot(
                settings, adapter, mode=settings.stackraise_context_mode.value
            )
            return {
                "warnings": snapshot.get("extraction", {}).get("warnings", []),
                "security_warnings": snapshot.get("security", {}).get("warnings", []),
            }
        except Exception as exc:
            return {"error": str(exc)}
