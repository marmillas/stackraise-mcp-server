"""Shared provider for Stackraise deep module context."""

from __future__ import annotations

import time
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any, TypedDict

from abstract_backend_mcp.context.extractors_static import (
    build_module_tree_from_index,
    build_stackraise_module_inventory,
)
from abstract_backend_mcp.context.schemas import (
    ModuleIndexEntry,
    ModuleTreeNode,
    StackraiseModules,
    SymbolIndexEntry,
)

if TYPE_CHECKING:
    from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
    from abstract_backend_mcp.core.settings import MCPSettings


class StackraiseContextProvider:
    """Build and cache deep Stackraise module context for snapshot and tools."""

    def __init__(self, settings: MCPSettings, adapter: StackraiseAdapter) -> None:
        self._settings = settings
        self._adapter = adapter
        self._lock = RLock()
        self._cache: dict[tuple[Any, ...], _CacheEntry] = {}
        self._fingerprint_cache: _FingerprintSnapshot | None = None

    def get_modules_context(
        self,
        *,
        mode: str,
        include_source: bool,
        apply_budget: bool,
    ) -> tuple[StackraiseModules, list[str], bool]:
        """Return Stackraise module context with optional runtime merge and budget."""
        cache_key = (
            mode,
            include_source,
            apply_budget,
            self._settings.project_root,
            self._settings.stackraise_package_name,
            self._settings.enable_deep_stackraise_context,
            self._settings.allow_runtime_context_imports,
            tuple(self._settings.stackraise_module_roots),
            self._settings.max_source_chunk_lines,
            self._settings.max_total_snapshot_items,
        )

        ttl_seconds = max(0, self._settings.stackraise_context_cache_ttl_seconds)
        now = time.monotonic()

        with self._lock:
            fingerprint = self._get_project_fingerprint(now)
            cached = self._cache.get(cache_key)
            if cached is not None and _is_cache_entry_valid(
                cached,
                fingerprint=fingerprint,
                now=now,
                ttl_seconds=ttl_seconds,
            ):
                return (
                    cached["modules"].model_copy(deep=True),
                    list(cached["warnings"]),
                    cached["fallback_used"],
                )

        warnings: list[str] = []
        fallback_used = False
        modules_context = self._build_static_inventory(include_source=include_source)
        detected_modules: dict[str, bool] = {}

        if mode in ("runtime", "hybrid"):
            if self._settings.allow_runtime_context_imports:
                try:
                    detected_modules = self._adapter.detect_modules()
                    modules_context.module_index = _merge_runtime_module_metadata(
                        modules_context.module_index,
                        self._adapter.get_runtime_module_metadata(detected_modules),
                    )
                    modules_context.symbol_index = _merge_runtime_symbol_index(
                        modules_context.symbol_index,
                        self._adapter.get_runtime_symbol_index(detected_modules),
                    )
                except Exception as exc:
                    fallback_used = True
                    warnings.append(f"Runtime extraction failed: {exc}")
            else:
                fallback_used = True
                warnings.append(
                    "Runtime context imports disabled by policy "
                    "(ALLOW_RUNTIME_CONTEXT_IMPORTS=false)"
                )
        elif mode == "static":
            try:
                detected_modules = self._adapter.detect_modules()
            except Exception:
                warnings.append("Module detection failed in static mode")

        modules_context.detected = detected_modules

        if apply_budget:
            modules_context, budget_warnings = _enforce_inventory_budget(
                modules_context,
                self._settings.max_total_snapshot_items,
            )
            warnings.extend(budget_warnings)

        with self._lock:
            fingerprint = self._get_project_fingerprint(now)
            self._cache[cache_key] = {
                "modules": modules_context.model_copy(deep=True),
                "warnings": list(warnings),
                "fallback_used": fallback_used,
                "fingerprint": fingerprint,
                "created_at": now,
            }
            self._trim_cache(
                max_entries=max(1, self._settings.stackraise_context_cache_max_entries)
            )

        return modules_context.model_copy(deep=True), warnings, fallback_used

    def _build_static_inventory(self, *, include_source: bool) -> StackraiseModules:
        if not self._settings.enable_deep_stackraise_context:
            return StackraiseModules()

        inventory = build_stackraise_module_inventory(
            self._settings.project_root,
            self._settings.stackraise_package_name,
            chunk_size=self._settings.max_source_chunk_lines,
            include_source=include_source,
            module_roots=self._settings.stackraise_module_roots,
        )
        return StackraiseModules.model_validate(inventory)

    def _build_project_fingerprint(self) -> tuple[int, int, int]:
        files = list(self._iter_stackraise_files())
        if not files:
            return (0, 0, 0)

        max_mtime_ns = 0
        total_size = 0
        count = 0
        for filepath in files:
            try:
                stat = filepath.stat()
            except OSError:
                continue

            count += 1
            max_mtime_ns = max(max_mtime_ns, stat.st_mtime_ns)
            total_size += stat.st_size

        return (count, max_mtime_ns, total_size)

    def _get_project_fingerprint(self, now: float) -> tuple[int, int, int]:
        ttl = max(0, self._settings.stackraise_context_fingerprint_ttl_seconds)
        if ttl > 0 and self._fingerprint_cache is not None:
            age = now - self._fingerprint_cache["created_at"]
            if age <= ttl:
                return self._fingerprint_cache["value"]

        fingerprint = self._build_project_fingerprint()
        self._fingerprint_cache = {
            "value": fingerprint,
            "created_at": now,
        }
        return fingerprint

    def _iter_stackraise_files(self):
        root = Path(self._settings.project_root)
        candidates: list[Path] = []

        if self._settings.stackraise_module_roots:
            for pattern in self._settings.stackraise_module_roots:
                candidates.extend(path for path in root.glob(pattern) if path.is_dir())
        else:
            candidates.extend(
                path
                for path in root.glob(f"**/{self._settings.stackraise_package_name}")
                if path.is_dir() and (path / "__init__.py").is_file()
            )

        seen: set[Path] = set()
        for candidate in sorted(set(candidates)):
            for filepath in candidate.rglob("*.py"):
                if filepath in seen:
                    continue
                if _should_skip_for_fingerprint(filepath):
                    continue
                seen.add(filepath)
                yield filepath

    def _trim_cache(self, *, max_entries: int) -> None:
        if len(self._cache) <= max_entries:
            return

        ordered = sorted(self._cache.items(), key=lambda item: item[1]["created_at"])
        to_drop = len(self._cache) - max_entries
        for idx in range(to_drop):
            self._cache.pop(ordered[idx][0], None)


class _CacheEntry(TypedDict):
    modules: StackraiseModules
    warnings: list[str]
    fallback_used: bool
    fingerprint: tuple[int, int, int]
    created_at: float


class _FingerprintSnapshot(TypedDict):
    value: tuple[int, int, int]
    created_at: float


def _is_cache_entry_valid(
    entry: _CacheEntry,
    *,
    fingerprint: tuple[int, int, int],
    now: float,
    ttl_seconds: int,
) -> bool:
    if entry["fingerprint"] != fingerprint:
        return False

    if ttl_seconds <= 0:
        return False

    age = now - entry["created_at"]
    return age <= ttl_seconds


def _should_skip_for_fingerprint(filepath: Path) -> bool:
    skip_dirs = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
    }
    return any(part in skip_dirs for part in filepath.parts)


def _enforce_inventory_budget(
    modules: StackraiseModules,
    max_items: int,
) -> tuple[StackraiseModules, list[str]]:
    if max_items <= 0:
        return modules, []

    warnings: list[str] = []
    budget = max_items

    module_index, budget = _truncate_field(
        list(modules.module_index),
        budget,
        "module_index",
        max_items,
        warnings,
    )

    module_tree_raw = build_module_tree_from_index([entry.model_dump() for entry in module_index])
    module_tree = [ModuleTreeNode.model_validate(item) for item in module_tree_raw]
    module_tree, budget = _truncate_field(
        module_tree,
        budget,
        "module_tree",
        max_items,
        warnings,
    )

    symbol_index, budget = _truncate_field(
        list(modules.symbol_index),
        budget,
        "symbol_index",
        max_items,
        warnings,
    )
    dependency_edges, budget = _truncate_field(
        list(modules.dependency_edges),
        budget,
        "dependency_edges",
        max_items,
        warnings,
    )
    content_catalog, _ = _truncate_field(
        list(modules.content_catalog),
        budget,
        "content_catalog",
        max_items,
        warnings,
    )

    updated = modules.model_copy(
        update={
            "module_index": module_index,
            "module_tree": module_tree,
            "symbol_index": symbol_index,
            "dependency_edges": dependency_edges,
            "content_catalog": content_catalog,
        }
    )
    return updated, warnings


def _truncate_field[T](
    items: list[T],
    budget: int,
    field: str,
    max_items: int,
    warnings: list[str],
) -> tuple[list[T], int]:
    if budget <= 0:
        if items:
            warnings.append(f"Truncated '{field}' due to max_total_snapshot_items={max_items}")
        return [], 0

    if len(items) <= budget:
        return items, budget - len(items)

    warnings.append(f"Truncated '{field}' due to max_total_snapshot_items={max_items}")
    return items[:budget], 0


def _merge_runtime_module_metadata(
    static_modules: list[ModuleIndexEntry],
    runtime_modules: list[dict[str, Any]],
) -> list[ModuleIndexEntry]:
    if not runtime_modules:
        return static_modules

    merged = [item.model_dump() for item in static_modules]
    by_module = {item.get("module", ""): item for item in merged}

    for runtime_item in runtime_modules:
        module_name = runtime_item.get("module", "")
        if not module_name:
            continue

        target = by_module.get(module_name)
        if target is None:
            target = {
                "module_id": runtime_item.get("module_id", f"mod:{module_name}"),
                "module": module_name,
                "package": runtime_item.get("package", module_name.rsplit(".", 1)[0]),
                "path": "",
                "kind": "runtime_module",
                "source": "runtime",
                "line_count": 0,
                "hash": "",
            }
            merged.append(target)
            by_module[module_name] = target

        target["runtime"] = runtime_item

    merged.sort(key=lambda item: item.get("module", ""))
    return [ModuleIndexEntry.model_validate(item) for item in merged]


def _merge_runtime_symbol_index(
    static_symbols: list[SymbolIndexEntry],
    runtime_symbols: list[dict[str, Any]],
) -> list[SymbolIndexEntry]:
    if not runtime_symbols:
        return static_symbols

    merged = [item.model_dump() for item in static_symbols]
    seen = {
        (
            item.get("module", ""),
            item.get("qualname", item.get("name", "")),
            item.get("kind", ""),
            item.get("source", ""),
        )
        for item in merged
    }

    for runtime_item in runtime_symbols:
        key = (
            runtime_item.get("module", ""),
            runtime_item.get("qualname", runtime_item.get("name", "")),
            runtime_item.get("kind", ""),
            runtime_item.get("source", "runtime"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(runtime_item)

    merged.sort(
        key=lambda item: (
            item.get("module", ""),
            item.get("line", 0),
            item.get("name", ""),
            item.get("source", ""),
        )
    )
    return [SymbolIndexEntry.model_validate(item) for item in merged]
