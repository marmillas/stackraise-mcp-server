"""Utilities for Stackraise module tree handling."""

from __future__ import annotations

from typing import Any


def build_module_tree(module_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def find_tree_node(nodes: list[dict[str, Any]], module_name: str) -> dict[str, Any] | None:
    for node in nodes:
        if node.get("module") == module_name:
            return node
        child = find_tree_node(list(node.get("children", [])), module_name)
        if child is not None:
            return child
    return None


def prune_tree_node(node: dict[str, Any], depth: int) -> dict[str, Any]:
    clone = dict(node)
    children = list(node.get("children", []))
    if depth <= 0:
        clone["children"] = []
        return clone

    clone["children"] = [prune_tree_node(child, depth - 1) for child in children]
    return clone


def _sort_tree_node(node: dict[str, Any]) -> None:
    node["children"].sort(key=lambda child: child["name"])
    for child in node["children"]:
        _sort_tree_node(child)
