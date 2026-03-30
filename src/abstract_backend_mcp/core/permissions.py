"""Write-operation permission checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from abstract_backend_mcp.core.errors import UnsafeOperationError

if TYPE_CHECKING:
    from abstract_backend_mcp.core.settings import MCPSettings

_UNSAFE_ENVIRONMENTS = {"production", "prod"}


def assert_write_allowed(settings: MCPSettings) -> None:
    """Raise if write operations are globally disabled."""
    if not settings.allow_write_operations:
        raise UnsafeOperationError(
            "Write operations are disabled. Set ALLOW_WRITE_OPERATIONS=true to enable."
        )


def assert_collection_allowed(settings: MCPSettings, collection: str) -> None:
    """Raise if the collection is not in the allow-list (when the list is non-empty)."""
    allowed = settings.allowed_write_collections
    if allowed and collection not in allowed:
        raise UnsafeOperationError(
            f"Collection '{collection}' is not in allowed_write_collections: {allowed}"
        )


def assert_environment_safe(settings: MCPSettings) -> None:
    """Raise if the current environment is considered unsafe for writes."""
    env = settings.environment.lower()
    if env in _UNSAFE_ENVIRONMENTS:
        raise UnsafeOperationError(
            f"Write operations are blocked in environment '{settings.environment}'."
        )


def normalize_write_request(
    settings: MCPSettings,
    collection: str,
    confirmed: bool = False,
) -> None:
    """Run all write precondition checks.

    Call this before any Mongo write operation.
    """
    assert_write_allowed(settings)
    assert_environment_safe(settings)
    assert_collection_allowed(settings, collection)

    if settings.require_write_confirmation and not confirmed:
        raise UnsafeOperationError(
            "Write requires explicit confirmation. Pass confirmed=True."
        )
