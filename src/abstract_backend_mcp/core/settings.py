"""MCP settings with Pydantic Settings, supporting .env and YAML overrides."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContextMode(StrEnum):
    STATIC = "static"
    RUNTIME = "runtime"
    HYBRID = "hybrid"


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project
    project_name: str = "my-project"
    environment: str = "development"
    project_root: str = Field(default_factory=lambda: str(Path.cwd()))

    # FastAPI
    fastapi_app_path: str = "app.main:app"
    enable_fastapi_tools: bool = True
    allow_fastapi_runtime_imports: bool = False

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mydb"
    enable_mongodb_tools: bool = True
    mongodb_sample_max_documents: int = 20

    # Stackraise
    stackraise_package_name: str = "stackraise"
    enable_stackraise_tools: bool = False

    # Test & quality
    enable_test_tools: bool = True
    enable_quality_tools: bool = True

    # Write controls
    allow_write_operations: bool = False
    require_write_confirmation: bool = True
    allowed_write_collections: list[str] = Field(default_factory=list)

    # Context / Stackraise extraction
    stackraise_context_mode: ContextMode = ContextMode.HYBRID
    allow_runtime_context_imports: bool = False
    enable_deep_stackraise_context: bool = True
    include_frontend_context: bool = False
    redact_sensitive_fields: bool = True
    stackraise_module_roots: list[str] = Field(default_factory=list)
    stackraise_domain_globs: list[str] = Field(default_factory=lambda: ["**/domain/**"])
    stackraise_api_globs: list[str] = Field(default_factory=lambda: ["**/api/**"])
    max_source_chunk_lines: int = 200
    max_total_snapshot_items: int = 500
    stackraise_search_max_pattern_length: int = 200
    stackraise_search_timeout_ms: int = 500
    stackraise_search_max_scanned_lines: int = 20000
    stackraise_context_cache_ttl_seconds: int = 30
    stackraise_context_cache_max_entries: int = 32
    stackraise_context_fingerprint_ttl_seconds: int = 1
    max_output_items: int = 50

    # Project instructions file
    project_instructions_file: str = "PROJECT.md"

    # YAML config path (optional override)
    config_file: str | None = None

    def __init__(self, _env_file: str | Path | None = ".env", **values: Any) -> None:
        """Expose `_env_file` explicitly for static type-checkers and tests."""
        super().__init__(_env_file=_env_file, **values)

    @model_validator(mode="before")
    @classmethod
    def merge_yaml_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        config_file = values.get("config_file") or values.get("CONFIG_FILE")
        if config_file:
            path = Path(config_file)
            if path.is_file():
                with open(path) as f:
                    yaml_data = yaml.safe_load(f) or {}
                # YAML values are lower priority than env/explicit — only fill gaps
                for key, val in yaml_data.items():
                    if key not in values or values[key] is None:
                        values[key] = val
        return values

    def sanitized_dict(self) -> dict[str, Any]:
        """Return settings dict with sensitive values redacted."""
        data = self.model_dump()
        sensitive_fragments = ("password", "secret", "token", "key", "uri")
        for key, value in list(data.items()):
            if isinstance(value, str) and any(
                fragment in key.lower() for fragment in sensitive_fragments
            ):
                data[key] = "***REDACTED***"

        from abstract_backend_mcp.context.redaction import sanitize_output_payload

        return sanitize_output_payload(data, redaction_enabled=True)
