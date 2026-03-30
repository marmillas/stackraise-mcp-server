"""Runtime context extractors – require the target app to be importable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.core.logging import get_logger

if TYPE_CHECKING:
    from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
    from abstract_backend_mcp.core.settings import MCPSettings

logger = get_logger()


def extract_runtime_context(
    settings: MCPSettings,
    adapter: StackraiseAdapter,
) -> dict[str, Any]:
    """Gather context by importing and introspecting live modules.

    Returns partial result + warnings if some modules fail.
    """
    warnings: list[str] = []
    context: dict[str, Any] = {}

    # Modules availability warning (module/symbol merge is handled by provider)
    if not adapter.is_available():
        warnings.append("Stackraise package not importable – skipping runtime extraction")

    # DB metadata
    try:
        context["db"] = adapter.get_db_metadata()
    except Exception as exc:
        context["db"] = {"available": False}
        warnings.append(f"DB metadata extraction failed: {exc}")

    # Auth
    try:
        context["auth"] = adapter.get_auth_metadata()
    except Exception as exc:
        context["auth"] = {"available": False}
        warnings.append(f"Auth metadata extraction failed: {exc}")

    # CRUD resources
    try:
        context["crud_resources"] = adapter.list_crud_resources()
    except Exception as exc:
        context["crud_resources"] = []
        warnings.append(f"CRUD resource listing failed: {exc}")

    # Workflows
    try:
        context["workflows"] = adapter.get_workflow_map()
    except Exception as exc:
        context["workflows"] = {}
        warnings.append(f"Workflow detection failed: {exc}")

    # Domain model
    try:
        context["domain_model"] = adapter.get_domain_model_graph()
    except Exception as exc:
        context["domain_model"] = {"available": False}
        warnings.append(f"Domain model extraction failed: {exc}")

    # FastAPI routes (via adapter if available)
    try:
        from abstract_backend_mcp.adapters.fastapi_adapter import FastAPIAdapter

        fa = FastAPIAdapter(settings.fastapi_app_path)
        context["routes"] = fa.list_routes()
        context["openapi_summary"] = fa.get_openapi_summary()
    except Exception as exc:
        context["routes"] = []
        context["openapi_summary"] = {}
        warnings.append(f"FastAPI route extraction failed: {exc}")

    context["_warnings"] = warnings
    return context
