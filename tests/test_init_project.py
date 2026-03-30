"""Tests for project bootstrap file generation."""

from __future__ import annotations

from abstract_backend_mcp.bootstrap.init_project import run_init


def test_run_init_generates_updated_stackraise_configs(tmp_path):
    target = tmp_path / "bootstrap-target"

    written = run_init(str(target))

    assert written
    env_example = (target / ".env.example").read_text()
    project_yaml = (target / "mcp.project.yaml").read_text()

    assert "STACKRAISE_ENABLED" not in env_example
    assert "ALLOW_FASTAPI_RUNTIME_IMPORTS=false" in env_example
    assert "MONGODB_SAMPLE_MAX_DOCUMENTS=20" in env_example
    assert "ALLOW_RUNTIME_CONTEXT_IMPORTS=false" in env_example
    assert "STACKRAISE_CONTEXT_CACHE_TTL_SECONDS=30" in env_example
    assert "STACKRAISE_CONTEXT_FINGERPRINT_TTL_SECONDS=1" in env_example
    assert "MAX_OUTPUT_ITEMS=50" in env_example

    assert "stackraise_enabled" not in project_yaml
    assert "allow_fastapi_runtime_imports: false" in project_yaml
    assert "mongodb_sample_max_documents: 20" in project_yaml
    assert "allow_runtime_context_imports: false" in project_yaml
    assert "stackraise_context_cache_ttl_seconds: 30" in project_yaml
    assert "stackraise_context_fingerprint_ttl_seconds: 1" in project_yaml
    assert "max_output_items: 50" in project_yaml
