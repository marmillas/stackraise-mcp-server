"""Helper functions for Stackraise navigation tools."""

from __future__ import annotations

import re
from typing import Any


def normalize_limit(limit: int, *, default: int = 50, max_limit: int = 200) -> int:
    if limit <= 0:
        return default
    return min(limit, max_limit)


def slice_page(
    items: list[dict[str, Any]],
    *,
    offset: int,
    limit: int,
    max_limit: int,
) -> list[dict[str, Any]]:
    safe_offset = max(offset, 0)
    safe_limit = normalize_limit(limit, max_limit=max_limit)
    return items[safe_offset : safe_offset + safe_limit]


def resolve_module_entry(
    module_id: str,
    module: str,
    inventory: dict[str, Any],
) -> dict[str, Any] | None:
    if module_id:
        return next(
            (
                entry
                for entry in inventory.get("module_index", [])
                if entry.get("module_id") == module_id
            ),
            None,
        )
    if module:
        return next(
            (entry for entry in inventory.get("module_index", []) if entry.get("module") == module),
            None,
        )
    return None


def build_chunk_for_range(
    *,
    lines: list[str],
    module_id: str,
    module: str,
    path: str,
    start_line: int,
    end_line: int,
) -> dict[str, Any]:
    chunk_lines = lines[start_line - 1 : end_line]
    return {
        "chunk_id": f"chunk:{module_id}:{start_line}-{end_line}",
        "module_id": module_id,
        "module": module,
        "path": path,
        "source": "static",
        "start_line": start_line,
        "end_line": end_line,
        "line_count": len(chunk_lines),
        "preview": "\n".join(chunk_lines[:3]),
        "content": "\n".join(chunk_lines),
    }


def parse_chunk_id_range(chunk_id: str, *, module_id: str) -> tuple[int, int] | None:
    prefix = f"chunk:{module_id}:"
    if not chunk_id.startswith(prefix):
        return None

    range_token = chunk_id[len(prefix) :]
    if "-" not in range_token:
        return None

    start_token, end_token = range_token.split("-", 1)
    try:
        start_line = int(start_token)
        end_line = int(end_token)
    except ValueError:
        return None

    if start_line < 1 or end_line < start_line:
        return None

    return start_line, end_line


def unsafe_regex_reason(pattern: str) -> str | None:
    if "(?<=" in pattern or "(?<!" in pattern:
        return "lookbehind assertions are not allowed"
    if "(?P<" in pattern:
        return "named groups are not allowed"
    if re.search(r"\\[1-9]", pattern):
        return "backreferences are not allowed"
    if re.search(r"\([^\n)]*[+*][^\n)]*\)[+*]", pattern):
        return "nested quantifiers are not allowed"
    return None
