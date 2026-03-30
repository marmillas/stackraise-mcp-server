"""Heuristic project detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_project(root: str | Path) -> dict[str, Any]:
    """Analyze a project directory and return detected features."""
    root = Path(root).resolve()
    result: dict[str, Any] = {
        "root": str(root),
        "has_poetry": False,
        "has_fastapi": False,
        "has_stackraise": False,
        "has_mongodb": False,
        "fastapi_app_path": None,
        "project_name": root.name,
    }

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text()
        result["has_poetry"] = "[tool.poetry]" in text
        result["has_fastapi"] = "fastapi" in text.lower()
        result["has_mongodb"] = "pymongo" in text.lower() or "motor" in text.lower()
        result["has_stackraise"] = "stackraise" in text.lower()

    # Try to find FastAPI app
    for candidate in [
        "app/main.py",
        "src/app/main.py",
        "main.py",
        "backend/src/demo/app.py",
    ]:
        if (root / candidate).is_file():
            mod = candidate.replace("/", ".").removesuffix(".py")
            result["fastapi_app_path"] = f"{mod}:app"
            break

    # Stackraise detection
    for sr_path in [
        "backend/src/stackraise",
        "src/stackraise",
        "stackraise",
    ]:
        if (root / sr_path).is_dir():
            result["has_stackraise"] = True
            break

    # Frontend detection
    result["has_frontend"] = any(
        (root / p).is_dir()
        for p in [
            "frontend/libs/@stackraise/core",
            "frontend",
        ]
    )

    return result
