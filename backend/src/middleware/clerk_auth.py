"""Clerk JWT verification middleware."""

import time

import httpx
import jwt
from fastapi import HTTPException, Request

from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)

_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600  # 1 hour

# Cache constructed RSA public key objects by kid to avoid
# re-parsing JWK on every verification.
_rsa_key_cache: dict[str, object] = {}


def _get_jwks() -> dict:
    """Fetch and cache Clerk's JWKS public keys."""
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache is not None and (time.monotonic() - _jwks_fetched_at < _JWKS_TTL):
        return _jwks_cache

    url = f"https://{settings.clerk_domain}/.well-known/jwks.json"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.monotonic()
        logger.info("clerk_jwks_fetched", domain=settings.clerk_domain)
        return _jwks_cache
    except httpx.HTTPError as e:
        logger.error("clerk_jwks_fetch_failed", error=str(e))
        raise HTTPException(503, "Auth service unavailable")


def clear_jwks_cache() -> None:
    """Clear the JWKS and RSA key caches (useful for key rotation or testing)."""
    global _jwks_cache, _jwks_fetched_at
    _jwks_cache = None
    _jwks_fetched_at = 0
    _rsa_key_cache.clear()


def verify_clerk_token(request: Request) -> dict:
    """Extract and verify Clerk JWT from Authorization header.

    Returns the decoded token payload.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ")

    try:
        unverified = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise HTTPException(401, "Invalid token format")

    kid = unverified.get("kid")
    if not kid:
        raise HTTPException(401, "Token missing key ID")

    jwks = _get_jwks()
    key_data = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
    if not key_data:
        # Key might have rotated — clear cache and retry once
        clear_jwks_cache()
        jwks = _get_jwks()
        key_data = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
        if not key_data:
            raise HTTPException(401, "Unknown signing key")

    try:
        if kid in _rsa_key_cache:
            public_key = _rsa_key_cache[kid]
        else:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            _rsa_key_cache[kid] = public_key
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=f"https://{settings.clerk_domain}",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning("clerk_token_invalid", error=str(e))
        raise HTTPException(401, "Invalid token")
