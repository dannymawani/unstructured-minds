"""Security and observability middleware for the Unstructured Minds API."""

from .clerk_auth import clear_jwks_cache, verify_clerk_token
from .rate_limit import limiter
from .request_logging import (
    REQUEST_ID_HEADER,
    RequestLoggingMiddleware,
    get_metrics,
)
from .security_headers import SecurityHeadersMiddleware
from .validation import (
    FileSizeError,
    PathValidationError,
    QueryValidationError,
    validate_file_path,
    validate_file_size,
    validate_query_length,
)

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
