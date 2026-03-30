"""Centralised logging for abstract-backend-mcp.

Uses standard library logging. Never emits to stdout directly to avoid
interfering with the MCP stdio transport.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

_logger: logging.Logger | None = None


def get_logger(name: str = "abstract-mcp") -> logging.Logger:
    """Return (and lazily configure) the package logger.

    Logs go to stderr so they don't collide with the MCP JSON-RPC stream on stdout.
    """
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.INFO)
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(_LOG_FORMAT))
            _logger.addHandler(handler)
    return _logger
