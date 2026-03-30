"""Tests for deep static module inventory extraction."""

from __future__ import annotations

import textwrap

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
from abstract_backend_mcp.context.extractors_static import build_stackraise_module_inventory
from abstract_backend_mcp.context.normalizer import build_snapshot
from abstract_backend_mcp.core.settings import MCPSettings


def test_build_stackraise_module_inventory_extracts_modules_symbols_and_chunks(tmp_path):
    pkg = tmp_path / "stackraise"
    auth_pkg = pkg / "auth"
    auth_pkg.mkdir(parents=True)

    (pkg / "__init__.py").write_text("from .db import User\n")
    (pkg / "db.py").write_text(
        textwrap.dedent(
            """\
            from .auth.scopes import DEFAULT_SCOPE

            VERSION = "1.0"

            class User:
                def save(self, payload: dict) -> None:
                    return None


            def build_user(name: str) -> User:
                return User()
            """
        )
    )
    (auth_pkg / "__init__.py").write_text("\n")
    (auth_pkg / "scopes.py").write_text("DEFAULT_SCOPE = 'admin'\n")

    inventory = build_stackraise_module_inventory(
        str(tmp_path),
        package_name="stackraise",
        chunk_size=4,
        include_source=True,
    )

    modules = {item["module"] for item in inventory["module_index"]}
    assert "stackraise" in modules
    assert "stackraise.db" in modules
    assert "stackraise.auth.scopes" in modules

    symbols = {item["qualname"] for item in inventory["symbol_index"]}
    assert "User" in symbols
    assert "User.save" in symbols
    assert "build_user" in symbols
    assert "VERSION" in symbols

    assert any(edge["target"] == "stackraise.db" for edge in inventory["dependency_edges"])
    assert any(edge["target"] == "stackraise.auth.scopes" for edge in inventory["dependency_edges"])
    assert any(
        chunk["module"] == "stackraise.db" and "content" in chunk
        for chunk in inventory["content_catalog"]
    )
    assert inventory["module_tree"][0]["module"] == "stackraise"


def test_build_stackraise_module_inventory_missing_package(tmp_path):
    inventory = build_stackraise_module_inventory(str(tmp_path), package_name="stackraise")
    assert inventory["module_tree"] == []
    assert inventory["module_index"] == []
    assert inventory["symbol_index"] == []
    assert inventory["dependency_edges"] == []
    assert inventory["content_catalog"] == []


def test_snapshot_contains_module_inventory_in_static_mode(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("\n")
    (pkg / "feature.py").write_text("def ping() -> str:\n    return 'ok'\n")

    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
    )
    adapter = StackraiseAdapter("nonexistent_package")
    snapshot = build_snapshot(settings, adapter, mode="static")

    modules = snapshot["stackraise"]["modules"]
    assert len(modules["module_index"]) >= 2
    assert any(item["module"] == "stackraise.feature" for item in modules["module_index"])
    assert any(item["module"] == "stackraise.feature" for item in modules["content_catalog"])


def test_snapshot_inventory_budget_limit(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .feature import ping\n")
    (pkg / "feature.py").write_text(
        "VALUE = 1\n"
        "def ping() -> str:\n"
        "    return 'ok'\n"
    )

    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        max_total_snapshot_items=2,
    )
    adapter = StackraiseAdapter("nonexistent_package")
    snapshot = build_snapshot(settings, adapter, mode="static")

    modules = snapshot["stackraise"]["modules"]
    counted = (
        len(modules["module_index"])
        + len(modules["symbol_index"])
        + len(modules["dependency_edges"])
        + len(modules["content_catalog"])
    )
    assert counted <= 2
    assert any("max_total_snapshot_items" in msg for msg in snapshot["extraction"]["warnings"])
