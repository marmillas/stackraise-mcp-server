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


def redact_value(key: str, value: Any) -> Any:
    """Redact the value if the key looks sensitive."""
    if isinstance(value, str) and _SENSITIVE_KEYS_RE.search(key):
        return _REDACTED
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
