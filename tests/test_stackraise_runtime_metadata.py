"""Tests for runtime metadata enrichment in Stackraise adapter."""

from __future__ import annotations

import sys

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter


def test_runtime_module_and_symbol_metadata(tmp_path):
    package_dir = tmp_path / "stackraise"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("\n")
    (package_dir / "model.py").write_text(
        "class User:\n"
        "    def save(self, value: str) -> str:\n"
        "        return value\n"
        "\n"
        "def build_user(name: str) -> User:\n"
        "    return User()\n"
    )

    sys.path.insert(0, str(tmp_path))
    try:
        adapter = StackraiseAdapter("stackraise")
        modules = adapter.detect_modules()

        runtime_modules = adapter.get_runtime_module_metadata(modules)
        assert any(item["module"] == "stackraise.model" for item in runtime_modules)

        runtime_symbols = adapter.get_runtime_symbol_index(modules)
        assert any(
            item["module"] == "stackraise.model" and item["name"] == "User"
            for item in runtime_symbols
        )
        assert any(
            item["module"] == "stackraise.model" and item["name"] == "build_user"
            for item in runtime_symbols
        )
    finally:
        sys.path.remove(str(tmp_path))
        _purge_modules(prefix="stackraise")


def _purge_modules(prefix: str) -> None:
    keys = [name for name in sys.modules if name == prefix or name.startswith(f"{prefix}.")]
    for key in keys:
        sys.modules.pop(key, None)
