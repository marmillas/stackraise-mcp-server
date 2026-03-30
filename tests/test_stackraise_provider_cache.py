"""Tests for Stackraise context provider cache invalidation."""

from __future__ import annotations

import time

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
from abstract_backend_mcp.context.provider import StackraiseContextProvider
from abstract_backend_mcp.core.settings import MCPSettings


def test_provider_cache_reused_when_fingerprint_unchanged(tmp_path, monkeypatch):
    _write_stackraise_module(tmp_path, "def ping() -> str:\n    return 'ok'\n")
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        stackraise_context_cache_ttl_seconds=60,
        stackraise_context_fingerprint_ttl_seconds=0,
    )
    provider = StackraiseContextProvider(settings, StackraiseAdapter("nonexistent"))

    calls = 0
    original = provider._build_static_inventory

    def spy(*, include_source: bool):
        nonlocal calls
        calls += 1
        return original(include_source=include_source)

    monkeypatch.setattr(provider, "_build_static_inventory", spy)

    first, _, _ = provider.get_modules_context(
        mode="static",
        include_source=False,
        apply_budget=False,
    )
    second, _, _ = provider.get_modules_context(
        mode="static",
        include_source=False,
        apply_budget=False,
    )

    assert calls == 1
    assert first.module_index == second.module_index


def test_provider_cache_invalidated_when_files_change(tmp_path, monkeypatch):
    _write_stackraise_module(tmp_path, "def ping() -> str:\n    return 'ok'\n")
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        stackraise_context_cache_ttl_seconds=60,
        stackraise_context_fingerprint_ttl_seconds=0,
    )
    provider = StackraiseContextProvider(settings, StackraiseAdapter("nonexistent"))

    calls = 0
    original = provider._build_static_inventory

    def spy(*, include_source: bool):
        nonlocal calls
        calls += 1
        return original(include_source=include_source)

    monkeypatch.setattr(provider, "_build_static_inventory", spy)

    first, _, _ = provider.get_modules_context(
        mode="static",
        include_source=False,
        apply_budget=False,
    )
    _write_stackraise_module(
        tmp_path,
        "def ping() -> str:\n    return 'ok'\n\n"
        "def pong() -> str:\n    return 'ok'\n",
    )
    time.sleep(0.02)
    second, _, _ = provider.get_modules_context(
        mode="static",
        include_source=False,
        apply_budget=False,
    )

    assert calls == 2
    first_symbols = {item.name for item in first.symbol_index}
    second_symbols = {item.name for item in second.symbol_index}
    assert "pong" not in first_symbols
    assert "pong" in second_symbols


def test_provider_cache_ttl_zero_forces_refresh(tmp_path, monkeypatch):
    _write_stackraise_module(tmp_path, "def ping() -> str:\n    return 'ok'\n")
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        stackraise_context_cache_ttl_seconds=0,
    )
    provider = StackraiseContextProvider(settings, StackraiseAdapter("nonexistent"))

    calls = 0
    original = provider._build_static_inventory

    def spy(*, include_source: bool):
        nonlocal calls
        calls += 1
        return original(include_source=include_source)

    monkeypatch.setattr(provider, "_build_static_inventory", spy)

    provider.get_modules_context(mode="static", include_source=False, apply_budget=False)
    provider.get_modules_context(mode="static", include_source=False, apply_budget=False)

    assert calls == 2


def test_provider_fingerprint_cache_reused_with_short_ttl(tmp_path, monkeypatch):
    _write_stackraise_module(tmp_path, "def ping() -> str:\n    return 'ok'\n")
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        stackraise_context_cache_ttl_seconds=0,
        stackraise_context_fingerprint_ttl_seconds=5,
    )
    provider = StackraiseContextProvider(settings, StackraiseAdapter("nonexistent"))

    calls = 0
    original = provider._build_project_fingerprint

    def spy():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(provider, "_build_project_fingerprint", spy)

    provider.get_modules_context(mode="static", include_source=False, apply_budget=False)
    provider.get_modules_context(mode="static", include_source=False, apply_budget=False)

    assert calls == 1


def test_provider_fingerprint_cache_disabled_with_zero_ttl(tmp_path, monkeypatch):
    _write_stackraise_module(tmp_path, "def ping() -> str:\n    return 'ok'\n")
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        stackraise_package_name="stackraise",
        stackraise_context_cache_ttl_seconds=0,
        stackraise_context_fingerprint_ttl_seconds=0,
    )
    provider = StackraiseContextProvider(settings, StackraiseAdapter("nonexistent"))

    calls = 0
    original = provider._build_project_fingerprint

    def spy():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(provider, "_build_project_fingerprint", spy)

    provider.get_modules_context(mode="static", include_source=False, apply_budget=False)
    provider.get_modules_context(mode="static", include_source=False, apply_budget=False)

    assert calls >= 2


def _write_stackraise_module(tmp_path, service_content: str) -> None:
    pkg = tmp_path / "stackraise"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("from .service import ping\n")
    (pkg / "service.py").write_text(service_content)
