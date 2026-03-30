"""Dynamic tool registration based on settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from abstract_backend_mcp.core.logging import get_logger

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings

logger = get_logger()


def register_all_tools(server: FastMCP, settings: MCPSettings) -> list[str]:
    """Register tool groups according to settings flags.

    Returns list of group names that were registered.
    """
    registered: list[str] = []

    # Health tools are always registered
    from abstract_backend_mcp.tools.health import register as reg_health

    reg_health(server, settings)
    registered.append("health")

    if settings.enable_test_tools:
        from abstract_backend_mcp.tools.test_tools import register as reg_test

        reg_test(server, settings)
        registered.append("test")

    if settings.enable_quality_tools:
        from abstract_backend_mcp.tools.quality_tools import register as reg_quality

        reg_quality(server, settings)
        registered.append("quality")

    if settings.enable_fastapi_tools:
        from abstract_backend_mcp.tools.fastapi_tools import register as reg_fastapi

        reg_fastapi(server, settings)
        registered.append("fastapi")

    if settings.enable_mongodb_tools:
        from abstract_backend_mcp.tools.mongodb_tools import register as reg_mongo

        reg_mongo(server, settings)
        registered.append("mongodb")

    if settings.enable_stackraise_tools:
        from abstract_backend_mcp.tools.stackraise_tools import register as reg_stackraise

        reg_stackraise(server, settings)
        registered.append("stackraise")

    logger.info("Registered tool groups: %s", registered)
    return registered
