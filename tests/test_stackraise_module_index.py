"""Tests for Stackraise module index across extraction modes."""

from __future__ import annotations

import sys

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
from abstract_backend_mcp.context.normalizer import build_snapshot
from abstract_backend_mcp.core.settings import MCPSettings


def test_module_index_static_mode(tmp_path):
    _write_stackraise_project(tmp_path)
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        allow_runtime_context_imports=True,
    )

    snapshot = build_snapshot(settings, StackraiseAdapter("nonexistent"), mode="static")
    modules = snapshot["stackraise"]["modules"]["module_index"]

    assert any(item["module"] == "stackraise" for item in modules)
    assert any(item["module"] == "stackraise.model" for item in modules)
    assert all(item["source"] == "static" for item in modules)


def test_module_index_hybrid_mode_runtime_warning_with_static_data(tmp_path):
    _write_stackraise_project(tmp_path)
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        allow_runtime_context_imports=True,
    )

    snapshot = build_snapshot(settings, StackraiseAdapter("stackraise"), mode="hybrid")
    modules = snapshot["stackraise"]["modules"]["module_index"]

    assert len(modules) > 0
    assert any(
        "Stackraise package not importable" in msg
        for msg in snapshot["extraction"]["warnings"]
    )


def test_module_index_runtime_mode_merges_runtime_metadata(tmp_path):
    _write_stackraise_project(tmp_path)
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        allow_runtime_context_imports=True,
    )

    sys.path.insert(0, str(tmp_path))
    try:
        snapshot = build_snapshot(settings, StackraiseAdapter("stackraise"), mode="runtime")
    finally:
        sys.path.remove(str(tmp_path))
        _purge_modules(prefix="stackraise")

    modules = snapshot["stackraise"]["modules"]["module_index"]
    model_entry = next(item for item in modules if item["module"] == "stackraise.model")

    assert "runtime" in model_entry
    assert model_entry["runtime"]["source"] == "runtime"
    assert model_entry["runtime"]["exports_count"] >= 1


def test_runtime_budget_applies_after_runtime_merge(tmp_path):
    _write_stackraise_project(tmp_path)
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        allow_runtime_context_imports=True,
        max_total_snapshot_items=1,
    )

    sys.path.insert(0, str(tmp_path))
    try:
        snapshot = build_snapshot(settings, StackraiseAdapter("stackraise"), mode="runtime")
    finally:
        sys.path.remove(str(tmp_path))
        _purge_modules(prefix="stackraise")

    modules = snapshot["stackraise"]["modules"]
    counted = (
        len(modules["module_index"])
        + len(modules["module_tree"])
        + len(modules["symbol_index"])
        + len(modules["dependency_edges"])
        + len(modules["content_catalog"])
    )

    assert counted <= 1
    assert any("max_total_snapshot_items" in msg for msg in snapshot["extraction"]["warnings"])


def _write_stackraise_project(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .model import User\n")
    (pkg / "model.py").write_text(
        "__all__ = ['User', 'build_user']\n"
        "\n"
        "class User:\n"
        "    pass\n"
        "\n"
        "def build_user(name: str) -> User:\n"
        "    return User()\n"
    )


def _purge_modules(prefix: str) -> None:
    keys = [name for name in sys.modules if name == prefix or name.startswith(f"{prefix}.")]
    for key in keys:
        sys.modules.pop(key, None)
