"""Shared response envelope helpers for MCP tools."""

from __future__ import annotations

from typing import Any


def build_error_payload(
    *,
    code: str,
    message: str,
    retriable: bool,
    partial: bool = False,
    blocked: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": message,
        "blocked": blocked,
        "error_detail": {
            "code": code,
            "message": message,
            "retriable": retriable,
            "partial": partial,
        },
    }
    payload.update(extra)
    return payload
