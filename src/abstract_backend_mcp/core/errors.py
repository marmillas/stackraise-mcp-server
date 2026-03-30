"""Custom exceptions for abstract-backend-mcp."""


class MCPConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""


class ToolExecutionError(Exception):
    """Raised when a tool fails during execution."""


class UnsafeOperationError(Exception):
    """Raised when an unsafe operation is attempted without proper authorization."""


class DependencyNotAvailableError(Exception):
    """Raised when a required optional dependency is not installed."""


class ProjectDetectionError(Exception):
    """Raised when project auto-detection fails."""


class ContextExtractionError(Exception):
    """Raised when context extraction fails."""


class ContextRedactionError(Exception):
    """Raised when secret redaction encounters an error."""
