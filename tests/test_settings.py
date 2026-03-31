"""Tests for MCPSettings."""

import yaml

from abstract_backend_mcp.core.settings import ContextMode, MCPSettings


def test_defaults():
    s = MCPSettings(_env_file=None)
    assert s.project_name == "my-project"
    assert s.environment == "development"
    assert s.allow_write_operations is False
    assert s.redact_sensitive_fields is True
    assert s.allow_fastapi_runtime_imports is False
    assert s.mongodb_sample_max_documents == 20
    assert s.mongodb_sample_max_bytes == 65536
    assert s.mongodb_sample_max_field_chars == 2000
    assert s.stackraise_context_mode == ContextMode.HYBRID
    assert s.allow_runtime_context_imports is False
    assert s.enable_deep_stackraise_context is True
    assert s.max_source_chunk_lines == 200
    assert s.max_total_snapshot_items == 500
    assert s.stackraise_search_max_pattern_length == 200
    assert s.stackraise_search_timeout_ms == 500
    assert s.stackraise_search_max_scanned_lines == 20000
    assert s.stackraise_context_cache_ttl_seconds == 30
    assert s.stackraise_context_cache_max_entries == 32
    assert s.stackraise_context_fingerprint_ttl_seconds == 1


def test_env_override(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "test-proj")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("ALLOW_WRITE_OPERATIONS", "true")
    s = MCPSettings(_env_file=None)
    assert s.project_name == "test-proj"
    assert s.environment == "staging"
    assert s.allow_write_operations is True


def test_yaml_override(tmp_path):
    cfg = tmp_path / "mcp.yaml"
    cfg.write_text(yaml.dump({"project_name": "from-yaml", "max_output_items": 100}))
    s = MCPSettings(_env_file=None, config_file=str(cfg))
    assert s.project_name == "from-yaml"
    assert s.max_output_items == 100


def test_sanitized_dict():
    s = MCPSettings(
        _env_file=None,
        project_name="token=abc123",
        mongodb_uri="mongodb://secret:pass@host/db",
    )
    d = s.sanitized_dict()
    assert d["mongodb_uri"] == "***REDACTED***"
    assert d["project_name"] == "token=***REDACTED***"
