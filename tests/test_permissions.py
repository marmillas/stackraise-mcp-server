"""Tests for permission checks."""

import pytest

from abstract_backend_mcp.core.errors import UnsafeOperationError
from abstract_backend_mcp.core.permissions import (
    assert_collection_allowed,
    assert_environment_safe,
    assert_write_allowed,
    normalize_write_request,
)
from abstract_backend_mcp.core.settings import MCPSettings


def _settings(**overrides) -> MCPSettings:
    defaults = {
        "allow_write_operations": True,
        "require_write_confirmation": False,
        "environment": "development",
        "allowed_write_collections": [],
    }
    defaults.update(overrides)
    return MCPSettings(_env_file=None, **defaults)


def test_write_blocked_by_default():
    s = MCPSettings(_env_file=None)
    with pytest.raises(UnsafeOperationError, match="disabled"):
        assert_write_allowed(s)


def test_write_allowed():
    s = _settings(allow_write_operations=True)
    assert_write_allowed(s)  # should not raise


def test_collection_allowed_empty_list():
    s = _settings()
    assert_collection_allowed(s, "anything")  # empty = all allowed


def test_collection_blocked():
    s = _settings(allowed_write_collections=["users"])
    with pytest.raises(UnsafeOperationError, match="not in allowed"):
        assert_collection_allowed(s, "orders")


def test_collection_passes():
    s = _settings(allowed_write_collections=["users", "orders"])
    assert_collection_allowed(s, "users")


def test_production_blocked():
    s = _settings(environment="production")
    with pytest.raises(UnsafeOperationError, match="production"):
        assert_environment_safe(s)


def test_dev_safe():
    s = _settings(environment="development")
    assert_environment_safe(s)


def test_normalize_full_pass():
    s = _settings(
        allow_write_operations=True,
        require_write_confirmation=True,
        environment="development",
        allowed_write_collections=["users"],
    )
    normalize_write_request(s, "users", confirmed=True)


def test_normalize_missing_confirmation():
    s = _settings(
        allow_write_operations=True,
        require_write_confirmation=True,
        environment="development",
    )
    with pytest.raises(UnsafeOperationError, match="confirmation"):
        normalize_write_request(s, "users", confirmed=False)
