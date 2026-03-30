"""Static context extractors – analyse code/files without importing the target app."""

from __future__ import annotations

import ast
import glob
import hashlib
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


def build_stackraise_module_inventory(
    root: str,
    package_name: str = "stackraise",
    *,
    chunk_size: int = 250,
    include_source: bool = False,
    module_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Build a static inventory for Stackraise modules and symbols."""
    base_path = Path(root)
    package_roots = _resolve_package_roots(base_path, package_name, module_roots)

    module_index: list[dict[str, Any]] = []
    symbol_index: list[dict[str, Any]] = []
    dependency_edges: list[dict[str, Any]] = []
    content_catalog: list[dict[str, Any]] = []
    module_sources: dict[str, dict[str, Any]] = {}

    for package_root in package_roots:
        for filepath in sorted(package_root.rglob("*.py")):
            if _should_skip_python_file(filepath):
                continue

            module_name = _module_name_from_path(filepath, package_root)
            if not module_name:
                continue

            module_id = f"mod:{module_name}"
            rel_path = str(filepath.relative_to(base_path))
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            lines = source.splitlines()
            line_count = len(lines)
            module_kind = "package" if filepath.name == "__init__.py" else "module"
            package = module_name if module_kind == "package" else module_name.rsplit(".", 1)[0]

            module_meta = {
                "module_id": module_id,
                "module": module_name,
                "package": package,
                "path": rel_path,
                "kind": module_kind,
                "source": "static",
                "line_count": line_count,
                "hash": hashlib.sha1(source.encode("utf-8")).hexdigest()[:12],
            }
            module_index.append(module_meta)
            module_sources[module_name] = {
                "module_id": module_id,
                "module": module_name,
                "path": rel_path,
                "source": source,
            }

            content_catalog.extend(
                _build_content_chunks(
                    source=source,
                    module_id=module_id,
                    module=module_name,
                    path=rel_path,
                    chunk_size=chunk_size,
                    include_source=include_source,
                )
            )

    known_modules = {m["module"] for m in module_index}
    for module_name, source_data in module_sources.items():
        source = source_data["source"]
        try:
            tree = ast.parse(source, filename=source_data["path"])
        except SyntaxError:
            continue

        symbol_index.extend(
            _extract_symbols(
                tree=tree,
                module_id=source_data["module_id"],
                module=module_name,
                path=source_data["path"],
            )
        )
        dependency_edges.extend(
            _extract_dependency_edges(
                tree=tree,
                module_id=source_data["module_id"],
                module=module_name,
                path=source_data["path"],
                known_modules=known_modules,
            )
        )

    module_index.sort(key=lambda item: item["module"])
    symbol_index.sort(key=lambda item: (item["module"], item["line"], item["name"]))
    dependency_edges.sort(key=lambda item: (item["source_module"], item["line"], item["target"]))

    return {
        "module_tree": _build_module_tree(module_index),
        "module_index": module_index,
        "symbol_index": symbol_index,
        "dependency_edges": dependency_edges,
        "content_catalog": content_catalog,
    }


def build_module_tree_from_index(module_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build module tree from an existing module index."""
    return _build_module_tree(module_index)


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


def _find_package_roots(base_path: Path, package_name: str) -> list[Path]:
    roots: list[Path] = []
    for candidate in base_path.glob(f"**/{package_name}"):
        if not candidate.is_dir():
            continue
        if any(part.startswith(".") for part in candidate.parts):
            continue
        if "__pycache__" in candidate.parts:
            continue
        if (candidate / "__init__.py").is_file():
            roots.append(candidate)
    roots.sort()
    return roots


def _resolve_package_roots(
    base_path: Path,
    package_name: str,
    module_roots: list[str] | None,
) -> list[Path]:
    if not module_roots:
        return _find_package_roots(base_path, package_name)

    roots: set[Path] = set()
    for pattern in module_roots:
        for candidate in base_path.glob(pattern):
            if not candidate.is_dir():
                continue
            if (candidate / "__init__.py").is_file():
                roots.add(candidate)

    if not roots:
        return _find_package_roots(base_path, package_name)

    return sorted(roots)


def _should_skip_python_file(filepath: Path) -> bool:
    skip_dirs = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
    }
    return any(part in skip_dirs for part in filepath.parts)


def _module_name_from_path(filepath: Path, package_root: Path) -> str:
    rel_to_parent = filepath.relative_to(package_root.parent).with_suffix("")
    parts = list(rel_to_parent.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _build_module_tree(module_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    roots: dict[str, dict[str, Any]] = {}

    def ensure_node(dotted_name: str) -> dict[str, Any]:
        if dotted_name not in nodes:
            node_name = dotted_name.split(".")[-1]
            nodes[dotted_name] = {
                "name": node_name,
                "module": dotted_name,
                "module_id": f"mod:{dotted_name}",
                "kind": "namespace",
                "path": "",
                "children": [],
            }
        return nodes[dotted_name]

    for module in module_index:
        dotted = module["module"]
        parts = dotted.split(".")
        for idx in range(len(parts)):
            current = ".".join(parts[: idx + 1])
            current_node = ensure_node(current)
            if idx == len(parts) - 1:
                current_node.update(
                    {
                        "module_id": module["module_id"],
                        "kind": module["kind"],
                        "path": module["path"],
                        "line_count": module["line_count"],
                        "hash": module["hash"],
                    }
                )

            if idx == 0:
                roots.setdefault(current, current_node)
                continue

            parent = ".".join(parts[:idx])
            parent_node = ensure_node(parent)
            if not any(child["module"] == current for child in parent_node["children"]):
                parent_node["children"].append(current_node)

    for root in roots.values():
        _sort_tree_node(root)

    return sorted(roots.values(), key=lambda node: node["module"])


def _sort_tree_node(node: dict[str, Any]) -> None:
    node["children"].sort(key=lambda child: child["name"])
    for child in node["children"]:
        _sort_tree_node(child)


def _extract_symbols(
    *,
    tree: ast.AST,
    module_id: str,
    module: str,
    path: str,
) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef):
            class_symbol = {
                "symbol_id": f"sym:{module_id}:{node.name}:{node.lineno}",
                "module_id": module_id,
                "module": module,
                "name": node.name,
                "qualname": node.name,
                "kind": "class",
                "source": "static",
                "line": node.lineno,
                "end_line": node.end_lineno or node.lineno,
                "path": path,
                "bases": [_base_name(base) for base in node.bases],
                "decorators": [_base_name(dec) for dec in node.decorator_list],
                "docstring": ast.get_docstring(node) or "",
            }
            symbols.append(class_symbol)

            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_name = f"{node.name}.{member.name}"
                    symbols.append(
                        {
                            "symbol_id": f"sym:{module_id}:{method_name}:{member.lineno}",
                            "module_id": module_id,
                            "module": module,
                            "name": member.name,
                            "qualname": method_name,
                            "kind": "method",
                            "source": "static",
                            "line": member.lineno,
                            "end_line": member.end_lineno or member.lineno,
                            "path": path,
                            "decorators": [_base_name(dec) for dec in member.decorator_list],
                            "args": [arg.arg for arg in member.args.args],
                            "docstring": ast.get_docstring(member) or "",
                        }
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "symbol_id": f"sym:{module_id}:{node.name}:{node.lineno}",
                    "module_id": module_id,
                    "module": module,
                    "name": node.name,
                    "qualname": node.name,
                    "kind": "function",
                    "source": "static",
                    "line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "path": path,
                    "decorators": [_base_name(dec) for dec in node.decorator_list],
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node) or "",
                }
            )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(
                        {
                            "symbol_id": f"sym:{module_id}:{target.id}:{node.lineno}",
                            "module_id": module_id,
                            "module": module,
                            "name": target.id,
                            "qualname": target.id,
                            "kind": "constant",
                            "source": "static",
                            "line": node.lineno,
                            "end_line": node.end_lineno or node.lineno,
                            "path": path,
                        }
                    )
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id.isupper():
                symbols.append(
                    {
                        "symbol_id": f"sym:{module_id}:{node.target.id}:{node.lineno}",
                        "module_id": module_id,
                        "module": module,
                        "name": node.target.id,
                        "qualname": node.target.id,
                        "kind": "constant",
                        "source": "static",
                        "line": node.lineno,
                        "end_line": node.end_lineno or node.lineno,
                        "path": path,
                    }
                )

    return symbols


def _extract_dependency_edges(
    *,
    tree: ast.AST,
    module_id: str,
    module: str,
    path: str,
    known_modules: set[str],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                key = (target, node.lineno)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "edge_id": f"dep:{module_id}:{target}:{node.lineno}",
                        "source_module_id": module_id,
                        "source_module": module,
                        "target": target,
                        "line": node.lineno,
                        "kind": "import",
                        "source": "static",
                        "internal": _is_internal_module(target, known_modules),
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_from_import_target(
                module=module,
                import_from=node,
                is_package=path.endswith("__init__.py"),
            )
            if not target:
                continue
            key = (target, node.lineno)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                {
                    "edge_id": f"dep:{module_id}:{target}:{node.lineno}",
                    "source_module_id": module_id,
                    "source_module": module,
                    "target": target,
                    "line": node.lineno,
                    "kind": "from_import",
                    "source": "static",
                    "internal": _is_internal_module(target, known_modules),
                }
            )

    return edges


def _is_internal_module(target: str, known_modules: set[str]) -> bool:
    if target in known_modules:
        return True
    return any(target.startswith(f"{known}.") for known in known_modules)


def _resolve_from_import_target(
    module: str,
    import_from: ast.ImportFrom,
    *,
    is_package: bool,
) -> str:
    if import_from.level == 0:
        return import_from.module or ""

    package_parts = module.split(".") if is_package else module.split(".")[:-1]
    trim = import_from.level - 1
    if trim > len(package_parts):
        base_parts: list[str] = []
    else:
        base_parts = package_parts[: len(package_parts) - trim]

    if import_from.module:
        base_parts.extend(import_from.module.split("."))
    return ".".join(base_parts)


def _build_content_chunks(
    *,
    source: str,
    module_id: str,
    module: str,
    path: str,
    chunk_size: int,
    include_source: bool,
) -> list[dict[str, Any]]:
    lines = source.splitlines()
    if not lines:
        empty_chunk: dict[str, Any] = {
            "chunk_id": f"chunk:{module_id}:1-1",
            "module_id": module_id,
            "module": module,
            "path": path,
            "source": "static",
            "start_line": 1,
            "end_line": 1,
            "line_count": 0,
            "preview": "",
        }
        if include_source:
            empty_chunk["content"] = ""
        return [empty_chunk]

    chunks: list[dict[str, Any]] = []
    for idx in range(0, len(lines), chunk_size):
        chunk_lines = lines[idx : idx + chunk_size]
        start_line = idx + 1
        end_line = idx + len(chunk_lines)
        chunk: dict[str, Any] = {
            "chunk_id": f"chunk:{module_id}:{start_line}-{end_line}",
            "module_id": module_id,
            "module": module,
            "path": path,
            "source": "static",
            "start_line": start_line,
            "end_line": end_line,
            "line_count": len(chunk_lines),
            "preview": "\n".join(chunk_lines[:3]),
        }
        if include_source:
            chunk["content"] = "\n".join(chunk_lines)
        chunks.append(chunk)
    return chunks
