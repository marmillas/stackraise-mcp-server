"""Static context extractors – analyse code/files without importing the target app."""

from __future__ import annotations

import ast
import glob
from pathlib import Path
from typing import Any

from abstract_backend_mcp.core.logging import get_logger

logger = get_logger()


def find_document_classes(root: str, domain_globs: list[str]) -> list[dict[str, Any]]:
    """Scan Python files for classes inheriting from db.Document-like bases."""
    results: list[dict[str, Any]] = []
    base_path = Path(root)

    for pattern in domain_globs:
        for filepath in glob.glob(str(base_path / pattern / "*.py"), recursive=True):
            try:
                tree = ast.parse(Path(filepath).read_text(), filename=filepath)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = [_base_name(b) for b in node.bases]
                    if any("Document" in b for b in bases if b):
                        results.append(
                            {
                                "name": node.name,
                                "file": str(Path(filepath).relative_to(base_path)),
                                "bases": bases,
                                "line": node.lineno,
                            }
                        )
    return results


def find_fastapi_routers(root: str, api_globs: list[str]) -> list[dict[str, Any]]:
    """Scan for APIRouter instantiations and route decorators."""
    results: list[dict[str, Any]] = []
    base_path = Path(root)

    for pattern in api_globs:
        for filepath in glob.glob(str(base_path / pattern / "*.py"), recursive=True):
            try:
                source = Path(filepath).read_text()
                tree = ast.parse(source, filename=filepath)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    func_name = _call_name(node.value)
                    if func_name and "Router" in func_name:
                        results.append(
                            {
                                "file": str(Path(filepath).relative_to(base_path)),
                                "type": "router",
                                "name": _target_name(node),
                                "line": node.lineno,
                            }
                        )
    return results


def detect_frontend_packages(root: str) -> list[str]:
    """Look for known Stackraise frontend packages."""
    packages: list[str] = []
    base = Path(root)
    for candidate in [
        "frontend/libs/@stackraise/core",
        "frontend/libs/@stackraise/auth",
    ]:
        if (base / candidate).is_dir():
            packages.append(candidate)
    return packages


def detect_workflow_files(root: str) -> dict[str, list[str]]:
    """Detect workflow-related files (RPA, email, templating)."""
    result: dict[str, list[str]] = {"rpa": [], "email": [], "templating": []}
    base = Path(root)

    for pattern, key in [
        ("**/ai/**/*.py", "rpa"),
        ("**/io/**/*.py", "email"),
        ("**/templating/**/*.py", "templating"),
    ]:
        for fp in glob.glob(str(base / pattern), recursive=True):
            rel = str(Path(fp).relative_to(base))
            if not rel.endswith("__init__.py"):
                result[key].append(rel)
    return result


# --- helpers ---

def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_base_name(node.value)}.{node.attr}"
    return ""


def _call_name(node: ast.Call) -> str:
    return _base_name(node.func) if isinstance(node.func, (ast.Name, ast.Attribute)) else ""


def _target_name(node: ast.Assign) -> str:
    if node.targets and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return ""
