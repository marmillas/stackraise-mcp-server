"""Context normalizer – builds the unified ContextSnapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.bootstrap.detect_project import detect_project
from abstract_backend_mcp.context.extractors_static import (
    detect_frontend_packages,
    detect_workflow_files,
    find_document_classes,
    find_fastapi_routers,
)
from abstract_backend_mcp.context.redaction import check_security_warnings, redact_dict
from abstract_backend_mcp.context.schemas import (
    APIContext,
    AuthContext,
    ContextSnapshot,
    DomainContext,
    ExtractionMeta,
    FrontendContracts,
    ProjectContext,
    SecurityContext,
    StackraiseContext,
    StackraiseModules,
    WorkflowContext,
)
from abstract_backend_mcp.core.logging import get_logger

if TYPE_CHECKING:
    from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
    from abstract_backend_mcp.core.settings import MCPSettings

logger = get_logger()


def build_snapshot(
    settings: MCPSettings,
    adapter: StackraiseAdapter,
    *,
    mode: str = "hybrid",
) -> dict[str, Any]:
    """Build a full context snapshot with the chosen extraction strategy."""
    warnings: list[str] = []
    fallback_used = False
    root = settings.project_root

    # --- project ---
    proj_info = detect_project(root)
    project = ProjectContext(
        name=settings.project_name,
        root=root,
        environment=settings.environment,
        has_poetry=proj_info.get("has_poetry", False),
        has_fastapi=proj_info.get("has_fastapi", False),
        has_mongodb=proj_info.get("has_mongodb", False),
        has_stackraise=proj_info.get("has_stackraise", False),
    )

    # --- static extraction ---
    documents = find_document_classes(root, settings.stackraise_domain_globs)
    routers = find_fastapi_routers(root, settings.stackraise_api_globs)
    frontend_pkgs = detect_frontend_packages(root) if settings.include_frontend_context else []
    workflow_files = detect_workflow_files(root)

    domain = DomainContext(documents=documents)
    api = APIContext(crud_resources=[], routes=[], openapi_summary={})
    auth = AuthContext()
    wf = WorkflowContext(
        rpa={"files": workflow_files.get("rpa", [])},
        email_watcher={"files": workflow_files.get("email", [])},
        doc_generation={"files": workflow_files.get("templating", [])},
    )
    fc = FrontendContracts(
        detected=bool(frontend_pkgs),
        packages=frontend_pkgs,
    )
    modules = StackraiseModules()

    # --- runtime extraction (if mode allows) ---
    if mode in ("runtime", "hybrid"):
        try:
            from abstract_backend_mcp.context.extractors_runtime import extract_runtime_context

            rt = extract_runtime_context(settings, adapter)
            modules = StackraiseModules(detected=rt.get("modules", {}))
            auth_data = rt.get("auth", {})
            auth = AuthContext(available=auth_data.get("available", False))
            api = APIContext(
                routes=rt.get("routes", []),
                crud_resources=rt.get("crud_resources", []),
                openapi_summary=rt.get("openapi_summary", {}),
            )
            rt_warnings = rt.get("_warnings", [])
            warnings.extend(rt_warnings)
        except Exception as exc:
            logger.warning("Runtime extraction failed, falling back to static: %s", exc)
            fallback_used = True
            warnings.append(f"Runtime extraction failed: {exc}")

    if mode == "static" or (mode == "hybrid" and fallback_used and not api.routes):
        # Fill API from static routers detection
        api.routes = [
            {"file": r["file"], "type": r["type"], "name": r.get("name", "")}
            for r in routers
        ]
        if mode == "hybrid":
            warnings.append("Using static API detection as fallback")

    # If pure static, detect modules via adapter anyway (safe)
    if mode == "static":
        try:
            modules = StackraiseModules(detected=adapter.detect_modules())
        except Exception:
            warnings.append("Module detection failed in static mode")

    # --- security ---
    sec_warnings = check_security_warnings(root)
    security = SecurityContext(
        redacted=settings.redact_sensitive_fields,
        warnings=sec_warnings,
    )

    # --- assemble ---
    snapshot = ContextSnapshot(
        project=project,
        stackraise=StackraiseContext(
            modules=modules,
            domain=domain,
            api=api,
            auth=auth,
            workflows=wf,
            frontend_contracts=fc,
        ),
        security=security,
        extraction=ExtractionMeta(
            mode=mode,
            fallback_used=fallback_used,
            warnings=warnings,
        ),
    )

    output = snapshot.model_dump()

    if settings.redact_sensitive_fields:
        output = redact_dict(output)

    return output
