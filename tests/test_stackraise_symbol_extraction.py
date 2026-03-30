"""Tests for static/runtime symbol extraction and fallback behavior."""

from __future__ import annotations

import sys

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
from abstract_backend_mcp.context.extractors_static import build_stackraise_module_inventory
from abstract_backend_mcp.context.normalizer import build_snapshot
from abstract_backend_mcp.core.settings import MCPSettings


def test_symbol_extraction_static_inventory(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("\n")
    (pkg / "service.py").write_text(
        "API_TOKEN = 'abc123'\n"
        "\n"
        "class Service:\n"
        "    def run(self) -> str:\n"
        "        return 'ok'\n"
        "\n"
        "def build_service() -> Service:\n"
        "    return Service()\n"
    )

    inventory = build_stackraise_module_inventory(str(tmp_path), package_name="stackraise")
    symbols = inventory["symbol_index"]

    assert any(item["qualname"] == "Service" and item["kind"] == "class" for item in symbols)
    assert any(item["qualname"] == "Service.run" and item["kind"] == "method" for item in symbols)
    assert any(item["qualname"] == "build_service" for item in symbols)
    assert any(item["qualname"] == "API_TOKEN" and item["kind"] == "constant" for item in symbols)


def test_symbol_extraction_runtime_merge(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("\n")
    (pkg / "model.py").write_text(
        "__all__ = ['User', 'build_user']\n"
        "\n"
        "class User:\n"
        "    def save(self, name: str) -> str:\n"
        "        return name\n"
        "\n"
        "def build_user(name: str) -> User:\n"
        "    return User()\n"
    )

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

    symbols = snapshot["stackraise"]["modules"]["symbol_index"]
    runtime_symbols = [item for item in symbols if item.get("source") == "runtime"]

    assert any(
        item["module"] == "stackraise.model" and item["name"] == "User"
        for item in runtime_symbols
    )
    assert any(
        item["module"] == "stackraise.model"
        and item["name"] == "build_user"
        and "signature" in item
        for item in runtime_symbols
    )


def test_symbol_docstring_redaction_in_snapshot(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("\n")
    (pkg / "service.py").write_text(
        "def leak() -> str:\n"
        "    \"\"\"Example API_KEY='abcd1234'\"\"\"\n"
        "    return 'ok'\n"
    )

    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        redact_sensitive_fields=True,
    )
    snapshot = build_snapshot(settings, StackraiseAdapter("nonexistent"), mode="static")

    symbols = snapshot["stackraise"]["modules"]["symbol_index"]
    leak_symbol = next(item for item in symbols if item["name"] == "leak")
    assert "abcd1234" not in leak_symbol["docstring"]
    assert "***REDACTED***" in leak_symbol["docstring"]


def _purge_modules(prefix: str) -> None:
    keys = [name for name in sys.modules if name == prefix or name.startswith(f"{prefix}.")]
    for key in keys:
        sys.modules.pop(key, None)
