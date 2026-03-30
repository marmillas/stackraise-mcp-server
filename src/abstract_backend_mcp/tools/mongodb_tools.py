"""MongoDB inspection and controlled-write tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.adapters.mongodb_adapter import MongoDBAdapter
from abstract_backend_mcp.context.redaction import sanitize_output_payload
from abstract_backend_mcp.core.errors import UnsafeOperationError
from abstract_backend_mcp.tools.response_helper import build_error_payload

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    adapter = MongoDBAdapter(settings)

    def sanitize(payload: Any) -> Any:
        return sanitize_output_payload(
            payload,
            redaction_enabled=settings.redact_sensitive_fields,
        )

    def normalize_sample_limit(limit: int) -> int:
        max_limit = max(1, settings.mongodb_sample_max_documents)
        if limit <= 0:
            return min(5, max_limit)
        return min(limit, max_limit)

    def error_payload(
        *,
        code: str,
        message: str,
        retriable: bool,
        blocked: bool = False,
    ) -> dict[str, Any]:
        return sanitize(
            build_error_payload(
                code=code,
                message=message,
                retriable=retriable,
                blocked=blocked,
            )
        )

    # --- readonly ---

    @server.tool(
        name="list_collections",
        description="List all MongoDB collections in the configured database.",
    )
    def list_collections() -> dict[str, Any]:
        try:
            collections = adapter.list_collections()
            return {"collections": collections, "total": len(collections)}
        except Exception as exc:
            return error_payload(
                code="MONGODB_LIST_COLLECTIONS_FAILED",
                message=str(exc),
                retriable=True,
            )

    @server.tool(
        name="sample_documents",
        description="Return sample documents from a collection.",
    )
    def sample_documents(collection: str, limit: int = 5) -> dict[str, Any]:
        try:
            safe_limit = normalize_sample_limit(limit)
            docs = adapter.sample_documents(collection, safe_limit)
            return sanitize(
                {
                    "collection": collection,
                    "limit": safe_limit,
                    "count": len(docs),
                    "documents": docs,
                }
            )
        except Exception as exc:
            return error_payload(
                code="MONGODB_SAMPLE_DOCUMENTS_FAILED",
                message=str(exc),
                retriable=True,
            )

    @server.tool(
        name="count_documents",
        description="Count documents in a collection, optionally with a filter.",
    )
    def count_documents(collection: str, filter_json: str = "{}") -> dict[str, Any]:
        try:
            filter_ = json.loads(filter_json)
            count = adapter.count_documents(collection, filter_)
            return sanitize({"collection": collection, "count": count})
        except json.JSONDecodeError as exc:
            return error_payload(
                code="MONGODB_INVALID_FILTER_JSON",
                message=f"Invalid JSON filter: {exc}",
                retriable=False,
            )
        except Exception as exc:
            return error_payload(
                code="MONGODB_COUNT_DOCUMENTS_FAILED",
                message=str(exc),
                retriable=True,
            )

    @server.tool(
        name="show_indexes",
        description="Show indexes for a MongoDB collection.",
    )
    def show_indexes(collection: str) -> dict[str, Any]:
        try:
            return sanitize({"collection": collection, "indexes": adapter.show_indexes(collection)})
        except Exception as exc:
            return error_payload(
                code="MONGODB_SHOW_INDEXES_FAILED",
                message=str(exc),
                retriable=True,
            )

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
            return error_payload(
                code="MONGODB_WRITE_BLOCKED",
                message=str(exc),
                retriable=False,
                blocked=True,
            )
        except json.JSONDecodeError as exc:
            return error_payload(
                code="MONGODB_INVALID_DOCUMENT_JSON",
                message=f"Invalid JSON document: {exc}",
                retriable=False,
            )
        except Exception as exc:
            return error_payload(
                code="MONGODB_INSERT_ONE_FAILED",
                message=str(exc),
                retriable=True,
            )

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
            return error_payload(
                code="MONGODB_WRITE_BLOCKED",
                message=str(exc),
                retriable=False,
                blocked=True,
            )
        except json.JSONDecodeError as exc:
            return error_payload(
                code="MONGODB_INVALID_UPDATE_JSON",
                message=f"Invalid JSON: {exc}",
                retriable=False,
            )
        except Exception as exc:
            return error_payload(
                code="MONGODB_UPDATE_ONE_FAILED",
                message=str(exc),
                retriable=True,
            )

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
            return error_payload(
                code="MONGODB_WRITE_BLOCKED",
                message=str(exc),
                retriable=False,
                blocked=True,
            )
        except json.JSONDecodeError as exc:
            return error_payload(
                code="MONGODB_INVALID_FILTER_JSON",
                message=f"Invalid JSON filter: {exc}",
                retriable=False,
            )
        except Exception as exc:
            return error_payload(
                code="MONGODB_DELETE_ONE_FAILED",
                message=str(exc),
                retriable=True,
            )
