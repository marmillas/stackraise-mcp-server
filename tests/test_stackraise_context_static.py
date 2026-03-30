"""Tests for the Stackraise context system (static extraction)."""

import textwrap

from abstract_backend_mcp.context.extractors_static import (
    detect_frontend_packages,
    find_document_classes,
)
from abstract_backend_mcp.context.redaction import check_security_warnings, redact_dict


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
