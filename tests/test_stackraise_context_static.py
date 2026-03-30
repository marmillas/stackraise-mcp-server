"""Tests for the Stackraise context system (static extraction)."""

import textwrap

from abstract_backend_mcp.context.extractors_static import (
    detect_frontend_packages,
    find_document_classes,
)
from abstract_backend_mcp.context.redaction import (
    check_security_warnings,
    redact_dict,
    sanitize_output_payload,
)


def test_find_document_classes(tmp_path):
    domain = tmp_path / "domain"
    domain.mkdir()
    (domain / "user.py").write_text(
        textwrap.dedent("""\
        from stackraise.db import Document

        class User(Document):
            name: str
        """)
    )
    results = find_document_classes(str(tmp_path), ["domain"])
    assert len(results) == 1
    assert results[0]["name"] == "User"


def test_no_documents(tmp_path):
    domain = tmp_path / "domain"
    domain.mkdir()
    (domain / "empty.py").write_text("x = 1\n")
    results = find_document_classes(str(tmp_path), ["domain"])
    assert results == []


def test_redact_dict():
    data = {
        "name": "hello",
        "password": "secret123",
        "nested": {"api_key": "abc", "value": 42},
    }
    redacted = redact_dict(data)
    assert redacted["name"] == "hello"
    assert redacted["password"] == "***REDACTED***"
    assert redacted["nested"]["api_key"] == "***REDACTED***"
    assert redacted["nested"]["value"] == 42


def test_redact_dict_textual_sensitive_literals():
    data = {
        "symbol": {
            "docstring": (
                "Credentials\n"
                "API_KEY='abc123'\n"
                "password = \"secret\"\n"
                "Authorization: Bearer token12345678\n"
            )
        },
        "content": "curl https://host/path?token=abc123",
    }

    redacted = redact_dict(data)
    assert "abc123" not in redacted["symbol"]["docstring"]
    assert "secret" not in redacted["symbol"]["docstring"]
    assert "token12345678" not in redacted["symbol"]["docstring"]
    assert "***REDACTED***" in redacted["symbol"]["docstring"]
    assert redacted["content"].endswith("token=***REDACTED***")


def test_redact_dict_textual_non_sensitive_content_unchanged():
    text = "This module uses a token bucket algorithm and returns a value"
    data = {"docstring": text}
    redacted = redact_dict(data)
    assert redacted["docstring"] == text


def test_sanitize_output_payload_handles_dict_list_and_string():
    payload = {
        "content": "API_KEY='secret123'",
        "items": [{"preview": "Bearer token12345678"}],
    }

    sanitized_dict = sanitize_output_payload(payload, redaction_enabled=True)
    assert sanitized_dict["content"] == "API_KEY=***REDACTED***"
    assert "token12345678" not in sanitized_dict["items"][0]["preview"]

    sanitized_list = sanitize_output_payload(["token=abc123"], redaction_enabled=True)
    assert sanitized_list[0] == "token=***REDACTED***"

    raw_string = sanitize_output_payload("token=abc123", redaction_enabled=False)
    assert raw_string == "token=abc123"


def test_security_warnings_env(tmp_path):
    (tmp_path / ".env").write_text("MONGODB_PASSWORD=secret\nNORMAL_VAR=ok\n")
    warnings = check_security_warnings(str(tmp_path))
    assert any("MONGODB_PASSWORD" in w for w in warnings)
    assert any(".gitignore" in w for w in warnings)


def test_security_warnings_gitignore_present(tmp_path):
    (tmp_path / ".env").write_text("API_KEY=x\n")
    (tmp_path / ".gitignore").write_text(".env\n")
    warnings = check_security_warnings(str(tmp_path))
    assert any("API_KEY" in w for w in warnings)
    assert not any(".gitignore" in w for w in warnings)


def test_detect_frontend_packages(tmp_path):
    (tmp_path / "frontend" / "libs" / "@stackraise" / "core").mkdir(parents=True)
    pkgs = detect_frontend_packages(str(tmp_path))
    assert "frontend/libs/@stackraise/core" in pkgs
