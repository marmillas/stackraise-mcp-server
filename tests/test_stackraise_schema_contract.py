"""Tests for typed Stackraise schema contract models."""

from __future__ import annotations

from abstract_backend_mcp.context.schemas import (
    ContentChunkEntry,
    ModuleIndexEntry,
    ModuleTreeNode,
    StackraiseModules,
    SymbolIndexEntry,
)


def test_stackraise_modules_preserve_extra_runtime_fields():
    modules = StackraiseModules(
        module_tree=[
            ModuleTreeNode(
                name="stackraise",
                module="stackraise",
                module_id="mod:stackraise",
                kind="package",
                path="stackraise/__init__.py",
                children=[
                    ModuleTreeNode(
                        name="db",
                        module="stackraise.db",
                        module_id="mod:stackraise.db",
                        kind="module",
                        path="stackraise/db.py",
                    )
                ],
            )
        ],
        module_index=[
            ModuleIndexEntry.model_validate(
                {
                    "module_id": "mod:stackraise.db",
                    "module": "stackraise.db",
                    "package": "stackraise",
                    "path": "stackraise/db.py",
                    "kind": "module",
                    "source": "static",
                    "line_count": 10,
                    "hash": "abc",
                    "runtime": {"exports_count": 3},
                }
            )
        ],
        symbol_index=[
            SymbolIndexEntry.model_validate(
                {
                    "symbol_id": "sym:runtime:mod:stackraise.db:User",
                    "module_id": "mod:stackraise.db",
                    "module": "stackraise.db",
                    "name": "User",
                    "qualname": "User",
                    "kind": "class",
                    "source": "runtime",
                    "line": 0,
                    "end_line": 0,
                    "path": "",
                    "mro": ["User", "object"],
                }
            )
        ],
        content_catalog=[
            ContentChunkEntry.model_validate(
                {
                    "chunk_id": "chunk:mod:stackraise.db:1-3",
                    "module_id": "mod:stackraise.db",
                    "module": "stackraise.db",
                    "path": "stackraise/db.py",
                    "source": "static",
                    "start_line": 1,
                    "end_line": 3,
                    "line_count": 3,
                    "preview": "class User:",
                    "content": "class User:\n    pass",
                }
            )
        ],
    )

    dumped = modules.model_dump()
    assert dumped["module_index"][0]["runtime"]["exports_count"] == 3
    assert dumped["symbol_index"][0]["mro"][0] == "User"
    assert dumped["content_catalog"][0]["content"].startswith("class User")


def test_stackraise_chunk_schema_does_not_force_content_field():
    modules = StackraiseModules(
        content_catalog=[
            ContentChunkEntry(
                chunk_id="chunk:mod:stackraise.db:1-1",
                module_id="mod:stackraise.db",
                module="stackraise.db",
                path="stackraise/db.py",
                source="static",
                start_line=1,
                end_line=1,
                line_count=1,
                preview="x = 1",
            )
        ]
    )

    dumped = modules.model_dump()
    assert "content" not in dumped["content_catalog"][0]
