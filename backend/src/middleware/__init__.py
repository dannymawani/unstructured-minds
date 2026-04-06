"""Security and observability middleware for the Unstructured Minds API."""

from .rate_limit import limiter
from .request_logging import (
    RequestLoggingMiddleware,
    get_metrics,
    REQUEST_ID_HEADER,
)
from .security_headers import SecurityHeadersMiddleware
from .validation import (
    validate_file_path,
    validate_query_length,
    validate_file_size,
    PathValidationError,
    QueryValidationError,
    FileSizeError,
)
from .clerk_auth import verify_clerk_token, clear_jwks_cache

__all__ = [
    # Rate limiting
    "limiter",
    # Request logging and metrics
    "RequestLoggingMiddleware",
    "get_metrics",
    "REQUEST_ID_HEADER",
    # Security
    "SecurityHeadersMiddleware",
    # Validation
    "validate_file_path",
    "validate_query_length",
    "validate_file_size",
    "PathValidationError",
    "QueryValidationError",
    "FileSizeError",
    # Auth
    "verify_clerk_token",
    "clear_jwks_cache",
]
