"""Simple HTTP Basic Auth middleware for self-hosted deployments."""

import base64
import secrets

from fastapi import HTTPException, Request

from ..config import settings


def verify_basic_auth(request: Request) -> None:
    """Verify HTTP Basic Auth credentials from the Authorization header.

    Reads expected username/password from BASIC_AUTH_USERNAME and
    BASIC_AUTH_PASSWORD environment variables.

    Raises:
        HTTPException: 401 if credentials are missing or invalid.
    """
    expected_user = settings.basic_auth_username
    expected_pass = settings.basic_auth_password

    if not expected_user or not expected_pass:
        raise HTTPException(
            status_code=500,
            detail="Basic auth is enabled but BASIC_AUTH_USERNAME or BASIC_AUTH_PASSWORD is not set.",
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Use constant-time comparison to prevent timing attacks
    user_ok = secrets.compare_digest(username, expected_user)
    pass_ok = secrets.compare_digest(password, expected_pass)

    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
