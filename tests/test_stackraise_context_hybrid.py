"""Tests for hybrid context snapshot building."""

from abstract_backend_mcp.adapters.stackraise_adapter import StackraiseAdapter
from abstract_backend_mcp.context.normalizer import build_snapshot
from abstract_backend_mcp.core.settings import MCPSettings


def test_snapshot_static_mode(tmp_path):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        redact_sensitive_fields=True,
    )
    adapter = StackraiseAdapter("nonexistent_package")
    snapshot = build_snapshot(settings, adapter, mode="static")

    assert "project" in snapshot
    assert "stackraise" in snapshot
    assert "security" in snapshot
    assert "extraction" in snapshot
    assert snapshot["extraction"]["mode"] == "static"


def test_snapshot_hybrid_fallback(tmp_path):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        redact_sensitive_fields=False,
    )
    adapter = StackraiseAdapter("nonexistent_package")
    snapshot = build_snapshot(settings, adapter, mode="hybrid")

    assert snapshot["extraction"]["mode"] == "hybrid"
    # Should have warnings about runtime failure
    assert len(snapshot["extraction"]["warnings"]) > 0


def test_snapshot_schema_stability(tmp_path):
    """The snapshot schema should always have the same top-level keys."""
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
    )
    adapter = StackraiseAdapter("nonexistent_package")
    snapshot = build_snapshot(settings, adapter, mode="static")

    expected_keys = {"project", "stackraise", "security", "extraction"}
    assert set(snapshot.keys()) == expected_keys

    sr = snapshot["stackraise"]
    expected_sr_keys = {"modules", "domain", "api", "auth", "workflows", "frontend_contracts"}
    assert set(sr.keys()) == expected_sr_keys
