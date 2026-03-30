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

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mydb"
    enable_mongodb_tools: bool = True

    # Stackraise
    stackraise_enabled: bool = False
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
    include_frontend_context: bool = False
    redact_sensitive_fields: bool = True
    stackraise_domain_globs: list[str] = Field(default_factory=lambda: ["**/domain/**"])
    stackraise_api_globs: list[str] = Field(default_factory=lambda: ["**/api/**"])
    max_output_items: int = 50

    # Project instructions file
    project_instructions_file: str = "PROJECT.md"

    # YAML config path (optional override)
    config_file: str | None = None

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
        sensitive_keys = {"mongodb_uri"}
        data = self.model_dump()
        for key in sensitive_keys:
            if key in data and data[key]:
                data[key] = "***REDACTED***"
        return data
