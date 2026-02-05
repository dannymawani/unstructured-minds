"""Security headers middleware.

Adds security headers to all responses:
- X-Content-Type-Options: Prevents MIME type sniffing
- X-Frame-Options: Prevents clickjacking
- Content-Security-Policy: Controls resource loading
- X-XSS-Protection: Legacy XSS protection (for older browsers)
- Referrer-Policy: Controls referrer information
- Permissions-Policy: Controls browser features
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses."""

    # Default Content-Security-Policy for API server
    # More restrictive since we're an API, not serving HTML
    DEFAULT_CSP = (
        "default-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )

    def __init__(
        self,
        app,
        content_security_policy: str = DEFAULT_CSP,
        x_frame_options: str = "DENY",
        x_content_type_options: str = "nosniff",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str = "geolocation=(), microphone=(), camera=()",
    ):
        """Initialize security headers middleware.

        Args:
            app: ASGI application
            content_security_policy: CSP header value
            x_frame_options: X-Frame-Options header value
            x_content_type_options: X-Content-Type-Options header value
            referrer_policy: Referrer-Policy header value
            permissions_policy: Permissions-Policy header value
        """
        super().__init__(app)
        self.content_security_policy = content_security_policy
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response.

        Args:
            request: The incoming request
            call_next: Function to call next middleware/route

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = self.x_content_type_options
        response.headers["X-Frame-Options"] = self.x_frame_options
        response.headers["Content-Security-Policy"] = self.content_security_policy
        response.headers["Referrer-Policy"] = self.referrer_policy
        response.headers["Permissions-Policy"] = self.permissions_policy

        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response
