"""Secret redaction for context output."""

from __future__ import annotations

import re
from typing import Any

# Keys whose values should always be redacted
_SENSITIVE_KEYS_RE = re.compile(
    r"(password|secret|token|api_key|apikey|auth|credential|private_key|"
    r"access_key|session|cookie|jwt|bearer)",
    re.IGNORECASE,
)

_REDACTED = "***REDACTED***"

_ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b(password|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|"
    r"client[_-]?secret|jwt|bearer)\b(\s*[:=]\s*)(['\"])([^'\"\n]+)(\3)"
)

_ENV_SECRET_RE = re.compile(
    r"(?im)^\s*([A-Z0-9_]*(PASSWORD|SECRET|TOKEN|API_KEY|ACCESS_KEY|"
    r"PRIVATE_KEY|CLIENT_SECRET)[A-Z0-9_]*)\s*=\s*([^#\n]+)"
)

_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]{8,}")

_QUERY_TOKEN_RE = re.compile(r"(?i)(token=)[^&\s]+")


def redact_textual_content(text: str) -> str:
    """Redact sensitive literals embedded in generic text/code snippets."""
    redacted = _ASSIGNMENT_SECRET_RE.sub(r"\1\2\3***REDACTED***\5", text)
    redacted = _ENV_SECRET_RE.sub(r"\1=***REDACTED***", redacted)
    redacted = _BEARER_RE.sub("Bearer ***REDACTED***", redacted)
    redacted = _QUERY_TOKEN_RE.sub(r"\1***REDACTED***", redacted)
    return redacted


def redact_value(key: str, value: Any) -> Any:
    """Redact the value if the key looks sensitive."""
    if isinstance(value, str) and _SENSITIVE_KEYS_RE.search(key):
        return _REDACTED
    if isinstance(value, str):
        return redact_textual_content(value)
    return value


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Deep-redact sensitive fields in a dictionary."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, list):
            result[key] = [
                redact_dict(item) if isinstance(item, dict) else redact_value(key, item)
                for item in value
            ]
        else:
            result[key] = redact_value(key, value)
    return result


def sanitize_output_payload(payload: Any, *, redaction_enabled: bool) -> Any:
    """Return payload sanitized according to redaction policy."""
    if not redaction_enabled:
        return payload

    if isinstance(payload, dict):
        return redact_dict(payload)

    if isinstance(payload, list):
        return [
            redact_dict(item)
            if isinstance(item, dict)
            else redact_textual_content(item)
            if isinstance(item, str)
            else item
            for item in payload
        ]

    if isinstance(payload, str):
        return redact_textual_content(payload)

    return payload


def check_security_warnings(root: str) -> list[str]:
    """Return warnings about potential secret exposure in the project."""
    from pathlib import Path

    warnings: list[str] = []
    env_file = Path(root) / ".env"
    if env_file.is_file():
        try:
            content = env_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if _SENSITIVE_KEYS_RE.search(key):
                        warnings.append(
                            f"Sensitive key '{key}' found in .env — ensure it is not committed"
                        )
        except OSError:
            pass

    gitignore = Path(root) / ".gitignore"
    if gitignore.is_file():
        content = gitignore.read_text()
        if ".env" not in content:
            warnings.append(".env is not listed in .gitignore — risk of committing secrets")
    else:
        warnings.append("No .gitignore found — risk of committing secrets")

    return warnings
