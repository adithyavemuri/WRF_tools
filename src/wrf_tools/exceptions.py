class WRFToolsError(Exception):
    """Base exception for the package."""


class DataValidationError(WRFToolsError, ValueError):
    """Raised when model data do not meet an API contract."""


class OptionalDependencyError(WRFToolsError, ImportError):
    """Raised when an optional feature dependency is unavailable."""
