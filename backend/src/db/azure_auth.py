"""Azure Entra ID token acquisition for Postgres authentication."""

import time

from ..logging_config import get_logger

logger = get_logger(__name__)

POSTGRES_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"

_credential = None
_cached_token: str | None = None
_token_expires_at: float = 0


def get_azure_postgres_token() -> str:
    """Get an Entra ID access token for Postgres authentication.

    Caches the credential instance and the token itself, refreshing
    the token 5 minutes before expiry.
    """
    global _credential, _cached_token, _token_expires_at

    # Return cached token if still valid (with 5-min buffer)
    if _cached_token and time.time() < _token_expires_at - 300:
        return _cached_token

    if _credential is None:
        from azure.identity import DefaultAzureCredential

        _credential = DefaultAzureCredential()
        logger.info("azure_credential_initialized")

    token = _credential.get_token(POSTGRES_SCOPE)
    _cached_token = token.token
    _token_expires_at = token.expires_on
    logger.info("azure_postgres_token_acquired", expires_in=int(_token_expires_at - time.time()))
    return _cached_token
