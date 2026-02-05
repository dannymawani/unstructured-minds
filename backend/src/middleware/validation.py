"""Input validation utilities for security.

Provides validation functions for:
- File paths (prevent path traversal attacks)
- Query lengths (prevent DoS via large inputs)
- File sizes (prevent resource exhaustion)
"""

import re
from pathlib import Path, PurePosixPath


class PathValidationError(ValueError):
    """Raised when path validation fails."""

    pass


class QueryValidationError(ValueError):
    """Raised when query validation fails."""

    pass


class FileSizeError(ValueError):
    """Raised when file size exceeds limit."""

    pass


# Maximum lengths for various inputs
MAX_QUERY_LENGTH = 10000  # 10KB for natural language queries
MAX_SEARCH_QUERY_LENGTH = 500  # 500 chars for search queries
MAX_FILE_PATH_LENGTH = 1000  # 1000 chars for file paths
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB for file uploads

# Dangerous patterns in file paths
PATH_TRAVERSAL_PATTERNS = [
    r"\.\.",  # Parent directory traversal
    r"^/",  # Absolute paths (Unix)
    r"^[a-zA-Z]:",  # Absolute paths (Windows)
    r"^\\",  # UNC paths
    r"\x00",  # Null bytes
]

# Allowed file extensions for vault files
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".yaml", ".yml"}


def validate_file_path(
    path: str,
    base_path: Path | None = None,
    allow_any_extension: bool = False,
) -> str:
    """Validate a file path for security.

    Checks for:
    - Path traversal attempts (.., absolute paths)
    - Null bytes and other injection attempts
    - Path length limits
    - Allowed file extensions (optional)

    Args:
        path: The file path to validate
        base_path: Optional base path to resolve against
        allow_any_extension: If True, skip extension validation

    Returns:
        Normalized, validated path

    Raises:
        PathValidationError: If validation fails
    """
    if not path:
        raise PathValidationError("Path cannot be empty")

    if len(path) > MAX_FILE_PATH_LENGTH:
        raise PathValidationError(
            f"Path exceeds maximum length of {MAX_FILE_PATH_LENGTH} characters"
        )

    # Check for dangerous patterns
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            raise PathValidationError(f"Invalid path: contains prohibited pattern")

    # Normalize the path
    try:
        # Use PurePosixPath for consistent handling across platforms
        normalized = PurePosixPath(path)

        # Check each component for hidden files or suspicious names
        for part in normalized.parts:
            # Allow dotfiles but not parent traversal
            if part == "..":
                raise PathValidationError("Path traversal not allowed")
            # Check for null bytes embedded in path components
            if "\x00" in part:
                raise PathValidationError("Invalid characters in path")

    except Exception as e:
        raise PathValidationError(f"Invalid path format: {str(e)}")

    # Validate extension if required
    if not allow_any_extension:
        suffix = normalized.suffix.lower()
        if suffix and suffix not in ALLOWED_EXTENSIONS:
            raise PathValidationError(
                f"File extension '{suffix}' not allowed. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

    # If base_path provided, ensure resolved path stays within it
    if base_path is not None:
        try:
            full_path = (base_path / path).resolve()
            base_resolved = base_path.resolve()
            if not str(full_path).startswith(str(base_resolved)):
                raise PathValidationError("Path escapes base directory")
        except Exception as e:
            raise PathValidationError(f"Path resolution failed: {str(e)}")

    return str(normalized)


def validate_query_length(
    query: str,
    max_length: int = MAX_QUERY_LENGTH,
    query_type: str = "query",
) -> str:
    """Validate query string length.

    Args:
        query: The query string to validate
        max_length: Maximum allowed length
        query_type: Type of query for error message

    Returns:
        Validated query string (stripped of leading/trailing whitespace)

    Raises:
        QueryValidationError: If query exceeds maximum length
    """
    if query is None:
        raise QueryValidationError(f"{query_type.capitalize()} cannot be None")

    # Strip whitespace
    stripped = query.strip()

    if len(stripped) > max_length:
        raise QueryValidationError(
            f"{query_type.capitalize()} exceeds maximum length of {max_length} characters"
        )

    return stripped


def validate_file_size(
    size_bytes: int,
    max_size: int = MAX_FILE_SIZE_BYTES,
) -> None:
    """Validate file size is within limits.

    Args:
        size_bytes: Size in bytes
        max_size: Maximum allowed size in bytes

    Raises:
        FileSizeError: If size exceeds limit
    """
    if size_bytes > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise FileSizeError(
            f"File size ({actual_mb:.2f}MB) exceeds maximum of {max_mb:.2f}MB"
        )


def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize a SQL identifier (table name, column name).

    Only allows alphanumeric characters and underscores.

    Args:
        identifier: The identifier to sanitize

    Returns:
        Sanitized identifier

    Raises:
        ValueError: If identifier is invalid
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty")

    # Only allow alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        raise ValueError(
            f"Invalid identifier '{identifier}': "
            "must start with letter/underscore, contain only alphanumeric/underscore"
        )

    # Check for SQL reserved words that might cause issues
    reserved_words = {
        "select", "insert", "update", "delete", "drop", "truncate",
        "create", "alter", "grant", "revoke", "table", "database",
    }
    if identifier.lower() in reserved_words:
        raise ValueError(f"Identifier '{identifier}' is a reserved SQL keyword")

    return identifier
