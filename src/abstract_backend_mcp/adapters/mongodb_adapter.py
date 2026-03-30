"""MongoDB adapter – wraps pymongo with permission-aware operations."""

from __future__ import annotations

from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

from abstract_backend_mcp.core.errors import DependencyNotAvailableError
from abstract_backend_mcp.core.logging import get_logger
from abstract_backend_mcp.core.permissions import normalize_write_request
from abstract_backend_mcp.core.settings import MCPSettings

logger = get_logger()


class MongoDBAdapter:
    def __init__(self, settings: MCPSettings) -> None:
        self._settings = settings
        self._client: MongoClient | None = None  # type: ignore[type-arg]
        self._db: Database | None = None  # type: ignore[type-arg]

    def _connect(self) -> Database:  # type: ignore[type-arg]
        if self._db is not None:
            return self._db
        try:
            self._client = MongoClient(
                self._settings.mongodb_uri,
                serverSelectionTimeoutMS=5000,
            )
            self._db = self._client[self._settings.mongodb_db_name]
            # Verify connectivity
            self._client.admin.command("ping")
        except Exception as exc:
            raise DependencyNotAvailableError(
                f"Could not connect to MongoDB: {exc}"
            ) from exc
        return self._db

    # --- read operations ---

    def list_collections(self) -> list[str]:
        db = self._connect()
        return sorted(db.list_collection_names())

    def sample_documents(self, collection: str, limit: int = 5) -> list[dict[str, Any]]:
        db = self._connect()
        docs = list(db[collection].find().limit(limit))
        for doc in docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return docs

    def count_documents(self, collection: str, filter_: dict[str, Any] | None = None) -> int:
        db = self._connect()
        return db[collection].count_documents(filter_ or {})

    def show_indexes(self, collection: str) -> list[dict[str, Any]]:
        db = self._connect()
        return [
            {"name": name, **info}
            for name, info in db[collection].index_information().items()
        ]

    # --- write operations (controlled) ---

    def insert_one(
        self, collection: str, document: dict[str, Any], confirmed: bool = False
    ) -> dict[str, Any]:
        normalize_write_request(self._settings, collection, confirmed)
        db = self._connect()
        result = db[collection].insert_one(document)
        return {"inserted_id": str(result.inserted_id)}

    def update_one(
        self,
        collection: str,
        filter_: dict[str, Any],
        update: dict[str, Any],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        normalize_write_request(self._settings, collection, confirmed)
        db = self._connect()
        result = db[collection].update_one(filter_, update)
        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
        }

    def delete_one(
        self, collection: str, filter_: dict[str, Any], confirmed: bool = False
    ) -> dict[str, Any]:
        normalize_write_request(self._settings, collection, confirmed)
        db = self._connect()
        result = db[collection].delete_one(filter_)
        return {"deleted_count": result.deleted_count}
