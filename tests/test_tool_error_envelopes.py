"""Tests for standardized error envelopes across tool groups."""

from __future__ import annotations

from abstract_backend_mcp.adapters.fastapi_adapter import FastAPIAdapter
from abstract_backend_mcp.adapters.mongodb_adapter import MongoDBAdapter
from abstract_backend_mcp.core.server import create_server
from abstract_backend_mcp.core.settings import MCPSettings


def _tool_fn(server, name: str):
    tool = server._tool_manager.get_tool(name)
    assert tool is not None
    return tool.fn


def test_fastapi_runtime_imports_blocked_by_policy(tmp_path):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=True,
        enable_mongodb_tools=False,
        enable_stackraise_tools=False,
        fastapi_app_path="invalid.module:app",
    )
    server = create_server(settings)

    payload = _tool_fn(server, "list_routes")()

    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert payload["error_detail"]["code"] == "FASTAPI_RUNTIME_IMPORTS_BLOCKED"
    assert payload["error_detail"]["retriable"] is False


def test_fastapi_error_envelope_for_invalid_app_import_when_allowed(tmp_path):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=True,
        enable_mongodb_tools=False,
        enable_stackraise_tools=False,
        allow_fastapi_runtime_imports=True,
        fastapi_app_path="invalid.module:app",
    )
    server = create_server(settings)

    payload = _tool_fn(server, "list_routes")()

    assert payload["ok"] is False
    assert payload["error_detail"]["code"] == "FASTAPI_LIST_ROUTES_FAILED"
    assert payload["error_detail"]["retriable"] is True


def test_fastapi_success_payload_shape_without_data_duplication(tmp_path, monkeypatch):
    def fake_list_routes(self):
        return [{"path": "/ping", "methods": ["GET"], "name": "ping", "tags": []}]

    monkeypatch.setattr(FastAPIAdapter, "list_routes", fake_list_routes)

    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=True,
        enable_mongodb_tools=False,
        enable_stackraise_tools=False,
        allow_fastapi_runtime_imports=True,
        fastapi_app_path="invalid.module:app",
    )
    server = create_server(settings)

    payload = _tool_fn(server, "list_routes")()

    assert payload["ok"] is True
    assert payload["total"] == 1
    assert "data" not in payload


def test_mongodb_error_envelope_for_invalid_json(tmp_path):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=False,
        enable_mongodb_tools=True,
        enable_stackraise_tools=False,
    )
    server = create_server(settings)

    payload = _tool_fn(server, "count_documents")(collection="users", filter_json="{")

    assert payload["ok"] is False
    assert payload["error_detail"]["code"] == "MONGODB_INVALID_FILTER_JSON"
    assert payload["error_detail"]["retriable"] is False


def test_mongodb_write_blocked_has_structured_error(tmp_path):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=False,
        enable_mongodb_tools=True,
        enable_stackraise_tools=False,
        allow_write_operations=False,
    )
    server = create_server(settings)

    payload = _tool_fn(server, "insert_one_controlled")(
        collection="users",
        document_json='{"name":"Ada"}',
        confirmed=True,
    )

    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert payload["error_detail"]["code"] == "MONGODB_WRITE_BLOCKED"


def test_mongodb_sample_documents_limit_and_redaction(tmp_path, monkeypatch):
    captured_limit: int | None = None

    def fake_sample_documents(self, collection: str, limit: int = 5):
        nonlocal captured_limit
        captured_limit = limit
        return [
            {
                "email": "user@example.com",
                "password": "super-secret",
                "note": "Bearer token12345678",
            }
        ]

    monkeypatch.setattr(MongoDBAdapter, "sample_documents", fake_sample_documents)

    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=False,
        enable_mongodb_tools=True,
        enable_stackraise_tools=False,
        mongodb_sample_max_documents=2,
        redact_sensitive_fields=True,
    )
    server = create_server(settings)

    payload = _tool_fn(server, "sample_documents")(collection="users", limit=99)

    assert payload["limit"] == 2
    assert captured_limit == 2
    assert payload["documents"][0]["password"] == "***REDACTED***"
    assert "token12345678" not in payload["documents"][0]["note"]


def test_mongodb_write_success_payload_is_backward_compatible(tmp_path, monkeypatch):
    def fake_insert_one(self, collection: str, document: dict[str, str], confirmed: bool = False):
        return {"inserted_id": "abc123"}

    monkeypatch.setattr(MongoDBAdapter, "insert_one", fake_insert_one)

    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=False,
        enable_mongodb_tools=True,
        enable_stackraise_tools=False,
        allow_write_operations=True,
    )
    server = create_server(settings)

    payload = _tool_fn(server, "insert_one_controlled")(
        collection="users",
        document_json='{"name":"Ada"}',
        confirmed=True,
    )

    assert payload["ok"] is True
    assert payload["inserted_id"] == "abc123"
    assert "data" not in payload
