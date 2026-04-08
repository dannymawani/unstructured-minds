"""Rate limiting middleware using slowapi.

Rate limits are configured per endpoint based on resource intensity:
- High-frequency endpoints (search): 100/minute
- Claude API endpoints (query/natural, chat): 30/minute
- Extraction endpoints: 20/minute
- Import/export endpoints: 5/minute
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse


def _get_real_client_ip(request: Request) -> str:
    """Get real client IP, considering proxy headers.

    Checks X-Forwarded-For header first (for nginx/proxy setups),
    falls back to remote address.

    Args:
        request: Starlette request object

    Returns:
        Client IP address string
    """
    # Check for proxy headers (nginx sets these)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list; first is the client
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct remote address
    return get_remote_address(request)


# Initialize limiter with custom key function
limiter = Limiter(key_func=_get_real_client_ip)


# Rate limit constants (requests per minute)
RATE_LIMIT_SEARCH = "100/minute"
RATE_LIMIT_CLAUDE_API = "30/minute"  # query/natural, chat - Claude API costs
RATE_LIMIT_EXTRACTION = "20/minute"
RATE_LIMIT_IMPORT = "5/minute"
RATE_LIMIT_DEFAULT = "200/minute"  # For general endpoints


def get_rate_limit_handler() -> callable:
    """Get rate limit exceeded handler.

    Returns:
        Handler function for rate limit exceeded errors
    """
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        """Handle rate limit exceeded errors.

        Args:
            request: The request that exceeded the rate limit
            exc: The rate limit exception

        Returns:
            JSON response with 429 status code
        """
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "message": str(exc.detail),
                "retry_after": exc.detail if hasattr(exc, "detail") else "60 seconds",
            },
        )

    return rate_limit_exceeded_handler
