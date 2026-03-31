"""Stackraise introspection and context tools."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
from abstract_backend_mcp.context.module_tree_utils import (
    find_tree_node as _find_tree_node,
)
from abstract_backend_mcp.context.module_tree_utils import (
    prune_tree_node as _prune_tree_node,
)
from abstract_backend_mcp.context.provider import StackraiseContextProvider
from abstract_backend_mcp.context.redaction import sanitize_output_payload
from abstract_backend_mcp.tools.response_helper import build_error_payload
from abstract_backend_mcp.tools.stackraise_helpers import (
    build_chunk_for_range as _build_chunk_for_range,
)
from abstract_backend_mcp.tools.stackraise_helpers import (
    normalize_limit as _normalize_limit,
)
from abstract_backend_mcp.tools.stackraise_helpers import (
    parse_chunk_id_range as _parse_chunk_id_range,
)
from abstract_backend_mcp.tools.stackraise_helpers import (
    resolve_module_entry as _resolve_module_entry,
)
from abstract_backend_mcp.tools.stackraise_helpers import (
    slice_page as _slice_page,
)
from abstract_backend_mcp.tools.stackraise_helpers import (
    unsafe_regex_reason as _unsafe_regex_reason,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    adapter = StackraiseAdapter(settings.stackraise_package_name)
    provider = StackraiseContextProvider(settings, adapter)
    tool_max_items = max(1, settings.max_output_items)

    def sanitize(payload: Any) -> Any:
        return sanitize_output_payload(
            payload,
            redaction_enabled=settings.redact_sensitive_fields,
        )

    def error_payload(
        *,
        code: str,
        message: str,
        retriable: bool,
        partial: bool = False,
        **extra: Any,
    ) -> dict[str, Any]:
        payload = build_error_payload(
            code=code,
            message=message,
            retriable=retriable,
            partial=partial,
            **extra,
        )
        return sanitize(payload)

    def load_inventory(*, include_source: bool) -> dict[str, Any]:
        modules_context, _, _ = provider.get_modules_context(
            mode=settings.stackraise_context_mode.value,
            include_source=include_source,
            apply_budget=False,
        )
        return modules_context.model_dump()

    def normalize_tool_limit(limit: int, *, default: int = 50) -> int:
        return _normalize_limit(limit, default=default, max_limit=tool_max_items)

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
            return error_payload(
                code="STACKRAISE_SNAPSHOT_BUILD_FAILED",
                message=str(exc),
                retriable=True,
                partial=True,
                mode=effective_mode,
            )

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
            return error_payload(
                code="STACKRAISE_WARNINGS_READ_FAILED",
                message=str(exc),
                retriable=True,
            )

    @server.tool(
        name="list_stackraise_module_tree",
        description="List the full Stackraise module tree.",
    )
    def list_stackraise_module_tree(
        parent_module: str = "",
        depth: int = 0,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        inventory = load_inventory(include_source=False)
        roots = inventory.get("module_tree", [])
        safe_depth = max(0, depth)

        nodes = roots
        if parent_module:
            parent = _find_tree_node(roots, parent_module)
            if parent is None:
                return error_payload(
                    code="STACKRAISE_TREE_PARENT_NOT_FOUND",
                    message=f"Parent module '{parent_module}' not found",
                    retriable=False,
                )
            nodes = list(parent.get("children", []))

        safe_offset = max(offset, 0)
        safe_limit = normalize_tool_limit(limit)
        page = nodes[safe_offset : safe_offset + safe_limit]
        page = [_prune_tree_node(node, safe_depth) for node in page]
        return sanitize(
            {
                "enabled": settings.enable_deep_stackraise_context,
                "module_tree": page,
                "items": page,
                "offset": safe_offset,
                "limit": safe_limit,
                "depth": safe_depth,
                "parent_module": parent_module,
                "total_roots": len(roots),
                "total_nodes": len(nodes),
                "total_modules": len(inventory.get("module_index", [])),
            }
        )

    @server.tool(
        name="list_stackraise_modules",
        description="List indexed Stackraise modules with pagination.",
    )
    def list_stackraise_modules(
        module_prefix: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        inventory = load_inventory(include_source=False)
        modules = inventory.get("module_index", [])
        if module_prefix:
            modules = [m for m in modules if m.get("module", "").startswith(module_prefix)]

        safe_limit = normalize_tool_limit(limit)
        page = _slice_page(modules, offset=offset, limit=safe_limit, max_limit=tool_max_items)
        return {
            "items": page,
            "offset": max(offset, 0),
            "limit": safe_limit,
            "total": len(modules),
        }

    @server.tool(
        name="show_stackraise_module_symbols",
        description="Show symbols for a Stackraise module.",
    )
    def show_stackraise_module_symbols(
        module_id: str = "",
        module: str = "",
        kind: str = "",
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        inventory = load_inventory(include_source=False)
        symbols = inventory.get("symbol_index", [])

        if module_id:
            symbols = [s for s in symbols if s.get("module_id") == module_id]
        if module:
            symbols = [s for s in symbols if s.get("module") == module]
        if kind:
            symbols = [s for s in symbols if s.get("kind") == kind]

        safe_limit = normalize_tool_limit(limit)
        page = _slice_page(symbols, offset=offset, limit=safe_limit, max_limit=tool_max_items)
        return sanitize(
            {
                "items": page,
                "offset": max(offset, 0),
                "limit": safe_limit,
                "total": len(symbols),
            }
        )

    @server.tool(
        name="read_stackraise_module_chunk",
        description="Read module source chunks by module and line window.",
    )
    def read_stackraise_module_chunk(
        module_id: str = "",
        module: str = "",
        chunk_id: str = "",
        start_line: int = 1,
        limit: int = 200,
    ) -> dict[str, Any]:
        inventory = load_inventory(include_source=False)
        module_entry = _resolve_module_entry(module_id, module, inventory)
        if module_entry is None:
            return error_payload(
                code="STACKRAISE_MODULE_NOT_FOUND",
                message="Module not found",
                retriable=False,
            )

        module_id_value = module_entry.get("module_id", "")
        module_name = module_entry.get("module", "")
        path = module_entry.get("path", "")
        if not module_id_value or not path:
            return error_payload(
                code="STACKRAISE_MODULE_SOURCE_UNAVAILABLE",
                message="Module source path is unavailable",
                retriable=False,
            )

        filepath = Path(settings.project_root) / path
        try:
            lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            return error_payload(
                code="STACKRAISE_MODULE_SOURCE_READ_FAILED",
                message=f"Could not read module source: {exc}",
                retriable=True,
            )

        if chunk_id:
            chunk_range = _parse_chunk_id_range(chunk_id, module_id=module_id_value)
            if chunk_range is None:
                return error_payload(
                    code="STACKRAISE_CHUNK_NOT_FOUND",
                    message=f"Chunk '{chunk_id}' not found",
                    retriable=False,
                    module_id=module_id_value,
                )

            chunk_start, chunk_end = chunk_range
            if chunk_start > len(lines) or chunk_end > len(lines):
                return error_payload(
                    code="STACKRAISE_CHUNK_NOT_FOUND",
                    message=f"Chunk '{chunk_id}' not found",
                    retriable=False,
                    module_id=module_id_value,
                )

            chunk = _build_chunk_for_range(
                lines=lines,
                module_id=module_id_value,
                module=module_name,
                path=path,
                start_line=chunk_start,
                end_line=chunk_end,
            )
            chunk["chunk_id"] = chunk_id
            return sanitize({"module_id": module_id_value, "items": [chunk], "total": 1})

        safe_start = max(1, start_line)
        max_lines = min(_normalize_limit(limit), settings.max_source_chunk_lines)
        requested_end = safe_start + max_lines - 1
        effective_end = min(len(lines), requested_end)
        if safe_start > len(lines):
            return sanitize(
                {
                    "module_id": module_id_value,
                    "requested": {
                        "start_line": safe_start,
                        "end_line": requested_end,
                        "limit": max_lines,
                    },
                    "items": [],
                    "total": 0,
                }
            )

        chunk = _build_chunk_for_range(
            lines=lines,
            module_id=module_id_value,
            module=module_name,
            path=path,
            start_line=safe_start,
            end_line=effective_end,
        )

        return sanitize(
            {
                "module_id": module_id_value,
                "requested": {
                    "start_line": safe_start,
                    "end_line": requested_end,
                    "limit": max_lines,
                },
                "items": [chunk],
                "total": 1,
            }
        )

    @server.tool(
        name="search_stackraise_code",
        description="Search code inside Stackraise modules.",
    )
    def search_stackraise_code(
        pattern: str,
        module_filter: str = "",
        limit: int = 50,
        case_sensitive: bool = False,
        use_regex: bool = False,
    ) -> dict[str, Any]:
        inventory = load_inventory(include_source=False)
        max_results = normalize_tool_limit(limit)

        if not pattern:
            return error_payload(
                code="STACKRAISE_SEARCH_EMPTY_PATTERN",
                message="Pattern cannot be empty",
                retriable=False,
            )

        max_pattern_length = max(1, settings.stackraise_search_max_pattern_length)
        if len(pattern) > max_pattern_length:
            return error_payload(
                code="STACKRAISE_SEARCH_PATTERN_TOO_LONG",
                message=f"Pattern too long: {len(pattern)} > {max_pattern_length}",
                retriable=False,
            )

        regex: re.Pattern[str] | None = None
        literal_pattern = pattern if case_sensitive else pattern.lower()
        if use_regex:
            unsafe_reason = _unsafe_regex_reason(pattern)
            if unsafe_reason:
                return error_payload(
                    code="STACKRAISE_SEARCH_UNSAFE_REGEX",
                    message=f"Unsafe regex pattern: {unsafe_reason}",
                    retriable=False,
                )

            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as exc:
                return error_payload(
                    code="STACKRAISE_SEARCH_INVALID_REGEX",
                    message=f"Invalid regex pattern: {exc}",
                    retriable=False,
                )

        root = Path(settings.project_root)
        matches: list[dict[str, Any]] = []
        truncated = False
        aborted = False
        abort_reason = ""
        scanned_lines = 0
        max_scanned_lines = max(1, settings.stackraise_search_max_scanned_lines)
        timeout_ms = max(1, settings.stackraise_search_timeout_ms)
        start_time = time.monotonic()

        for module_item in inventory.get("module_index", []):
            module_name = module_item.get("module", "")
            if module_filter and module_filter not in module_name:
                continue

            path = module_item.get("path", "")
            if not path:
                continue

            filepath = root / path
            try:
                lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue

            for line_number, line in enumerate(lines, start=1):
                scanned_lines += 1
                if scanned_lines > max_scanned_lines:
                    aborted = True
                    abort_reason = (
                        "Search aborted: line budget exceeded "
                        f"({max_scanned_lines})"
                    )
                    break

                elapsed_ms = (time.monotonic() - start_time) * 1000
                if elapsed_ms > timeout_ms:
                    aborted = True
                    abort_reason = (
                        "Search aborted: timeout exceeded "
                        f"({timeout_ms} ms)"
                    )
                    break

                line_slice = line[:2000]
                if regex is not None:
                    found = regex.search(line_slice)
                    if not found:
                        continue
                    matched = found.group(0)
                else:
                    haystack = line_slice if case_sensitive else line_slice.lower()
                    index = haystack.find(literal_pattern)
                    if index < 0:
                        continue
                    matched = line_slice[index : index + len(pattern)]

                matches.append(
                    {
                        "module_id": module_item.get("module_id", ""),
                        "module": module_name,
                        "path": path,
                        "line": line_number,
                        "match": matched,
                        "preview": line.strip()[:300],
                    }
                )
                if len(matches) >= max_results:
                    truncated = True
                    break

            if truncated or aborted:
                break

        return sanitize(
            {
                "pattern": pattern,
                "use_regex": use_regex,
                "module_filter": module_filter,
                "items": matches,
                "total": len(matches),
                "truncated": truncated,
                "aborted": aborted,
                "abort_reason": abort_reason,
                "scanned_lines": scanned_lines,
            }
        )

    @server.tool(
        name="show_stackraise_symbol_source",
        description="Show source code for a symbol id.",
    )
    def show_stackraise_symbol_source(symbol_id: str) -> dict[str, Any]:
        inventory = load_inventory(include_source=False)
        symbol = next(
            (
                item
                for item in inventory.get("symbol_index", [])
                if item.get("symbol_id") == symbol_id
            ),
            None,
        )
        if symbol is None:
            return error_payload(
                code="STACKRAISE_SYMBOL_NOT_FOUND",
                message=f"Symbol '{symbol_id}' not found",
                retriable=False,
            )

        if symbol.get("source") == "runtime":
            return sanitize(
                {
                "symbol": symbol,
                "content": "",
                "note": "Runtime symbol has no static file source",
                }
            )

        path = symbol.get("path", "")
        start_line = int(symbol.get("line") or 0)
        end_line = int(symbol.get("end_line") or start_line)
        if not path or start_line <= 0:
            return sanitize(
                {
                "symbol": symbol,
                "content": "",
                "note": "No file location available for symbol",
                }
            )

        max_lines = settings.max_source_chunk_lines
        capped_end = min(end_line, start_line + max_lines - 1)
        filepath = Path(settings.project_root) / path

        try:
            lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            return error_payload(
                code="STACKRAISE_SYMBOL_SOURCE_READ_FAILED",
                message=f"Could not read symbol source: {exc}",
                retriable=True,
            )

        source = "\n".join(lines[start_line - 1 : capped_end])
        return sanitize(
            {
            "symbol": symbol,
            "path": path,
            "start_line": start_line,
            "end_line": capped_end,
            "content": source,
            "truncated": capped_end < end_line,
            }
        )

