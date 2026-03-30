"""Tests for Stackraise module navigation tools."""

from __future__ import annotations

import sys

from abstract_backend_mcp.core.server import create_server
from abstract_backend_mcp.core.settings import MCPSettings


def _build_server(
    tmp_path,
    *,
    enable_deep_stackraise_context: bool = True,
    stackraise_package_name: str = "stackraise",
    redact_sensitive_fields: bool = True,
    allow_runtime_context_imports: bool = False,
    stackraise_search_max_pattern_length: int = 200,
    stackraise_search_timeout_ms: int = 500,
    stackraise_search_max_scanned_lines: int = 20000,
    max_output_items: int = 50,
):
    settings = MCPSettings(
        _env_file=None,
        project_root=str(tmp_path),
        enable_test_tools=False,
        enable_quality_tools=False,
        enable_fastapi_tools=False,
        enable_mongodb_tools=False,
        enable_stackraise_tools=True,
        stackraise_package_name=stackraise_package_name,
        enable_deep_stackraise_context=enable_deep_stackraise_context,
        redact_sensitive_fields=redact_sensitive_fields,
        allow_runtime_context_imports=allow_runtime_context_imports,
        stackraise_search_max_pattern_length=stackraise_search_max_pattern_length,
        stackraise_search_timeout_ms=stackraise_search_timeout_ms,
        stackraise_search_max_scanned_lines=stackraise_search_max_scanned_lines,
        max_output_items=max_output_items,
    )
    return create_server(settings)


def _write_demo_stackraise(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .service import ping\nfrom .model import User\n")
    (pkg / "service.py").write_text(
        "VALUE = 1\n"
        "\n"
        "def ping() -> str:\n"
        "    return \"ok\"\n"
    )
    (pkg / "model.py").write_text(
        "__all__ = ['User', 'build_user']\n"
        "\n"
        "class User:\n"
        "    pass\n"
        "\n"
        "def build_user(name: str) -> User:\n"
        "    return User()\n"
    )


def _write_stackraise_with_secrets(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .secrets import leak\n")
    (pkg / "secrets.py").write_text(
        "API_KEY = \"abcd1234\"\n"
        "\n"
        "def leak() -> str:\n"
        "    \"\"\"Bearer token12345678\"\"\"\n"
        "    return API_KEY\n"
    )


def _write_stackraise_with_many_lines(tmp_path):
    pkg = tmp_path / "stackraise"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .bulk import marker\n")
    body = "".join(f"line_{idx} = {idx}\n" for idx in range(1, 30))
    (pkg / "bulk.py").write_text(body + "\nmarker = 'done'\n")


def _tool_fn(server, name: str):
    tool = server._tool_manager.get_tool(name)
    assert tool is not None
    return tool.fn


def test_navigation_tools_registered_and_list_modules(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)
    names = {tool.name for tool in server._tool_manager.list_tools()}

    expected = {
        "list_stackraise_module_tree",
        "list_stackraise_modules",
        "show_stackraise_module_symbols",
        "read_stackraise_module_chunk",
        "search_stackraise_code",
        "show_stackraise_symbol_source",
    }
    assert expected.issubset(names)

    list_modules = _tool_fn(server, "list_stackraise_modules")
    result = list_modules(module_prefix="stackraise", offset=0, limit=10)
    assert result["total"] >= 2
    assert any(item["module"] == "stackraise.service" for item in result["items"])

    list_tree = _tool_fn(server, "list_stackraise_module_tree")
    tree = list_tree()
    assert tree["total_modules"] >= 2
    assert tree["module_tree"][0]["module"] == "stackraise"


def test_navigation_tools_read_search_and_symbol_source(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    show_symbols = _tool_fn(server, "show_stackraise_module_symbols")
    symbols = show_symbols(module="stackraise.service", limit=50)
    assert symbols["total"] > 0

    ping_symbol = next(item for item in symbols["items"] if item["qualname"] == "ping")

    show_source = _tool_fn(server, "show_stackraise_symbol_source")
    source = show_source(symbol_id=ping_symbol["symbol_id"])
    assert "def ping" in source["content"]

    search_code = _tool_fn(server, "search_stackraise_code")
    matches = search_code(pattern="return \"ok\"", module_filter="stackraise.service")
    assert matches["total"] >= 1

    read_chunk = _tool_fn(server, "read_stackraise_module_chunk")
    chunk = read_chunk(module="stackraise.service", start_line=1, limit=20)
    assert chunk["total"] >= 1
    assert "content" in chunk["items"][0]


def test_navigation_chunk_id_roundtrip(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    read_chunk = _tool_fn(server, "read_stackraise_module_chunk")
    initial = read_chunk(module="stackraise.service", start_line=1, limit=20)
    assert initial["total"] >= 1

    chunk_id = initial["items"][0]["chunk_id"]
    by_id = read_chunk(module="stackraise.service", chunk_id=chunk_id)

    assert by_id["total"] == 1
    assert by_id["items"][0]["chunk_id"] == chunk_id
    assert by_id["items"][0]["content"] == initial["items"][0]["content"]


def test_navigation_tools_when_deep_context_disabled(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path, enable_deep_stackraise_context=False)

    list_tree = _tool_fn(server, "list_stackraise_module_tree")
    result = list_tree()
    assert result["enabled"] is False
    assert result["total_modules"] == 0


def test_snapshot_flow_static_hybrid_and_runtime(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path, allow_runtime_context_imports=True)
    build_snapshot = _tool_fn(server, "build_stackraise_context_snapshot")

    static_snapshot = build_snapshot(mode="static")
    assert static_snapshot["extraction"]["mode"] == "static"
    assert len(static_snapshot["stackraise"]["modules"]["module_index"]) >= 2

    hybrid_snapshot = build_snapshot(mode="hybrid")
    assert hybrid_snapshot["extraction"]["mode"] == "hybrid"
    assert len(hybrid_snapshot["extraction"]["warnings"]) > 0

    sys.path.insert(0, str(tmp_path))
    try:
        runtime_server = _build_server(tmp_path, allow_runtime_context_imports=True)
        runtime_snapshot = _tool_fn(runtime_server, "build_stackraise_context_snapshot")(
            mode="runtime"
        )
    finally:
        sys.path.remove(str(tmp_path))
        _purge_modules(prefix="stackraise")

    runtime_symbols = runtime_snapshot["stackraise"]["modules"]["symbol_index"]
    assert any(item.get("source") == "runtime" for item in runtime_symbols)


def test_snapshot_runtime_blocked_by_policy(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path, allow_runtime_context_imports=False)

    build_snapshot = _tool_fn(server, "build_stackraise_context_snapshot")
    snapshot = build_snapshot(mode="runtime")

    warnings = snapshot["extraction"]["warnings"]
    matches = [msg for msg in warnings if "ALLOW_RUNTIME_CONTEXT_IMPORTS=false" in msg]
    assert len(matches) == 1


def test_snapshot_flow_with_runtime_fallback(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(
        tmp_path,
        stackraise_package_name="nonexistent_stackraise",
        allow_runtime_context_imports=True,
    )

    build_snapshot = _tool_fn(server, "build_stackraise_context_snapshot")
    snapshot = build_snapshot(mode="hybrid")

    warnings = snapshot["extraction"]["warnings"]
    assert any("Stackraise package not importable" in msg for msg in warnings)
    assert snapshot["stackraise"]["modules"]["module_index"] == []


def test_navigation_tools_redact_sensitive_source_by_default(tmp_path):
    _write_stackraise_with_secrets(tmp_path)
    server = _build_server(tmp_path)

    read_chunk = _tool_fn(server, "read_stackraise_module_chunk")
    chunk_payload = read_chunk(module="stackraise.secrets", start_line=1, limit=20)
    content = "\n".join(item.get("content", "") for item in chunk_payload["items"])
    assert "abcd1234" not in content
    assert "token12345678" not in content
    assert "***REDACTED***" in content

    search_code = _tool_fn(server, "search_stackraise_code")
    matches = search_code(
        pattern="API_KEY = \"abcd1234\"",
        module_filter="stackraise.secrets",
    )
    assert matches["total"] >= 1
    assert "abcd1234" not in matches["items"][0]["preview"]

    show_symbols = _tool_fn(server, "show_stackraise_module_symbols")
    symbols = show_symbols(module="stackraise.secrets", limit=20)
    leak_symbol = next(item for item in symbols["items"] if item["qualname"] == "leak")
    assert "token12345678" not in leak_symbol.get("docstring", "")
    assert "***REDACTED***" in leak_symbol.get("docstring", "")

    show_source = _tool_fn(server, "show_stackraise_symbol_source")
    symbol_payload = show_source(symbol_id=leak_symbol["symbol_id"])
    assert "abcd1234" not in symbol_payload["content"]
    assert "token12345678" not in symbol_payload["content"]
    assert "***REDACTED***" in symbol_payload["content"]


def test_navigation_tools_allow_raw_source_when_redaction_disabled(tmp_path):
    _write_stackraise_with_secrets(tmp_path)
    server = _build_server(tmp_path, redact_sensitive_fields=False)

    read_chunk = _tool_fn(server, "read_stackraise_module_chunk")
    chunk_payload = read_chunk(module="stackraise.secrets", start_line=1, limit=20)
    content = "\n".join(item.get("content", "") for item in chunk_payload["items"])
    assert "abcd1234" in content


def test_search_guardrail_pattern_length(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path, stackraise_search_max_pattern_length=8)

    search_code = _tool_fn(server, "search_stackraise_code")
    payload = search_code(pattern="a" * 20)

    assert "Pattern too long" in payload["error"]
    assert payload["ok"] is False
    assert payload["error_detail"]["code"] == "STACKRAISE_SEARCH_PATTERN_TOO_LONG"
    assert payload["error_detail"]["retriable"] is False


def test_search_regex_mode_enabled(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    search_code = _tool_fn(server, "search_stackraise_code")
    payload = search_code(
        pattern=r"return\s+\"ok\"",
        module_filter="stackraise.service",
        use_regex=True,
    )

    assert payload["total"] >= 1
    assert payload["use_regex"] is True


def test_search_invalid_regex_error_envelope(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    search_code = _tool_fn(server, "search_stackraise_code")
    payload = search_code(pattern="(", use_regex=True)

    assert payload["ok"] is False
    assert payload["error_detail"]["code"] == "STACKRAISE_SEARCH_INVALID_REGEX"


def test_search_guardrail_line_budget_abort(tmp_path):
    _write_stackraise_with_many_lines(tmp_path)
    server = _build_server(tmp_path, stackraise_search_max_scanned_lines=5)

    search_code = _tool_fn(server, "search_stackraise_code")
    payload = search_code(pattern=r"this_will_not_match", module_filter="stackraise.bulk")

    assert payload["aborted"] is True
    assert "line budget exceeded" in payload["abort_reason"]


def test_read_chunk_respects_requested_line_limit(tmp_path):
    _write_stackraise_with_many_lines(tmp_path)
    server = _build_server(tmp_path)

    read_chunk = _tool_fn(server, "read_stackraise_module_chunk")
    payload = read_chunk(module="stackraise.bulk", start_line=1, limit=5)

    assert payload["total"] == 1
    chunk = payload["items"][0]
    assert chunk["line_count"] == 5
    assert chunk["start_line"] == 1
    assert chunk["end_line"] == 5
    assert len(chunk["content"].splitlines()) == 5


def test_error_envelope_for_missing_module_chunk(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    read_chunk = _tool_fn(server, "read_stackraise_module_chunk")
    payload = read_chunk(module="stackraise.unknown", start_line=1, limit=10)

    assert payload["ok"] is False
    assert payload["error"] == "Module not found"
    assert payload["error_detail"]["code"] == "STACKRAISE_MODULE_NOT_FOUND"
    assert payload["error_detail"]["retriable"] is False


def test_navigation_limits_respect_max_output_items(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path, max_output_items=1)

    list_tree = _tool_fn(server, "list_stackraise_module_tree")
    tree = list_tree(limit=10)
    assert tree["limit"] == 1
    assert len(tree["module_tree"]) <= 1

    list_modules = _tool_fn(server, "list_stackraise_modules")
    modules = list_modules(module_prefix="stackraise", limit=10)
    assert modules["limit"] == 1
    assert len(modules["items"]) <= 1

    show_symbols = _tool_fn(server, "show_stackraise_module_symbols")
    symbols = show_symbols(module="stackraise.model", limit=10)
    assert symbols["limit"] == 1
    assert len(symbols["items"]) <= 1


def test_module_tree_supports_parent_and_depth(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    list_tree = _tool_fn(server, "list_stackraise_module_tree")
    roots = list_tree(depth=0, limit=10)
    assert roots["total_roots"] >= 1
    assert roots["module_tree"][0]["children"] == []

    children = list_tree(parent_module="stackraise", depth=0, limit=10)
    assert children["total_nodes"] >= 1
    assert all(item["module"].startswith("stackraise.") for item in children["items"])


def test_module_tree_parent_not_found_error(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    list_tree = _tool_fn(server, "list_stackraise_module_tree")
    payload = list_tree(parent_module="stackraise.unknown")

    assert payload["ok"] is False
    assert payload["error_detail"]["code"] == "STACKRAISE_TREE_PARENT_NOT_FOUND"


def test_search_unsafe_regex_rejected(tmp_path):
    _write_demo_stackraise(tmp_path)
    server = _build_server(tmp_path)

    search_code = _tool_fn(server, "search_stackraise_code")
    payload = search_code(pattern=r"(a+)+$", use_regex=True)

    assert payload["ok"] is False
    assert payload["error_detail"]["code"] == "STACKRAISE_SEARCH_UNSAFE_REGEX"


def _purge_modules(prefix: str) -> None:
    keys = [name for name in sys.modules if name == prefix or name.startswith(f"{prefix}.")]
    for key in keys:
        sys.modules.pop(key, None)
