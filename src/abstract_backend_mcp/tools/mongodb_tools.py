"""MongoDB inspection and controlled-write tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.adapters.mongodb_adapter import MongoDBAdapter
from abstract_backend_mcp.core.errors import UnsafeOperationError

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    adapter = MongoDBAdapter(settings)

    # --- readonly ---

    @server.tool(
        name="list_collections",
        description="List all MongoDB collections in the configured database.",
    )
    def list_collections() -> dict[str, Any]:
        try:
            return {"collections": adapter.list_collections()}
        except Exception as exc:
            return {"error": str(exc)}

    @server.tool(
        name="sample_documents",
        description="Return sample documents from a collection.",
    )
    def sample_documents(collection: str, limit: int = 5) -> dict[str, Any]:
        try:
            docs = adapter.sample_documents(collection, limit)
            return {"collection": collection, "count": len(docs), "documents": docs}
        except Exception as exc:
            return {"error": str(exc)}

    @server.tool(
        name="count_documents",
        description="Count documents in a collection, optionally with a filter.",
    )
    def count_documents(collection: str, filter_json: str = "{}") -> dict[str, Any]:
        try:
            filter_ = json.loads(filter_json)
            count = adapter.count_documents(collection, filter_)
            return {"collection": collection, "count": count}
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON filter: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}

    @server.tool(
        name="show_indexes",
        description="Show indexes for a MongoDB collection.",
    )
    def show_indexes(collection: str) -> dict[str, Any]:
        try:
            return {"collection": collection, "indexes": adapter.show_indexes(collection)}
        except Exception as exc:
            return {"error": str(exc)}

    # --- controlled writes ---

    @server.tool(
        name="insert_one_controlled",
        description="Insert a document (requires write permissions + confirmation).",
    )
    def insert_one_controlled(
        collection: str, document_json: str, confirmed: bool = False
    ) -> dict[str, Any]:
        try:
            document = json.loads(document_json)
            return adapter.insert_one(collection, document, confirmed)
        except UnsafeOperationError as exc:
            return {"error": str(exc), "blocked": True}
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON document: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}

    @server.tool(
        name="update_one_controlled",
        description="Update one document (requires write permissions and confirmation).",
    )
    def update_one_controlled(
        collection: str,
        filter_json: str,
        update_json: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        try:
            filter_ = json.loads(filter_json)
            update = json.loads(update_json)
            return adapter.update_one(collection, filter_, update, confirmed)
        except UnsafeOperationError as exc:
            return {"error": str(exc), "blocked": True}
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}

    @server.tool(
        name="delete_one_controlled",
        description="Delete one document (requires write permissions and confirmation).",
    )
    def delete_one_controlled(
        collection: str, filter_json: str, confirmed: bool = False
    ) -> dict[str, Any]:
        try:
            filter_ = json.loads(filter_json)
            return adapter.delete_one(collection, filter_, confirmed)
        except UnsafeOperationError as exc:
            return {"error": str(exc), "blocked": True}
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON filter: {exc}"}
        except Exception as exc:
            return {"error": str(exc)}
