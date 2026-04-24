"""OAuth2 client_credentials token manager for Copernicus Data Space Ecosystem.

CDSE issues short-lived access tokens (~10 minutes). This manager fetches a
token lazily on first use, caches it in memory, and refreshes it ~60 seconds
before expiry so callers never hit a 401.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Refresh buffer: renew the token this many seconds before it actually expires,
# so a request that starts with a still-valid token can't fail mid-flight.
_REFRESH_BUFFER_SECONDS = 60


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # unix epoch seconds

    @property
    def is_valid(self) -> bool:
        return time.time() < (self.expires_at - _REFRESH_BUFFER_SECONDS)


class CDSETokenManager:
    """Fetches and caches an OAuth2 access token for CDSE Sentinel Hub."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self._settings = settings
        self._client = client
        self._token: _CachedToken | None = None
        # Lock prevents a token-refresh thundering herd when many requests
        # arrive simultaneously after the cached token expires.
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        """Return a valid access token, fetching/refreshing if needed."""
        if self._token and self._token.is_valid:
            return self._token.access_token

        async with self._lock:
            # Double-check: another coroutine may have refreshed while we waited.
            if self._token and self._token.is_valid:
                return self._token.access_token
            self._token = await self._fetch_token()
            return self._token.access_token

    async def _fetch_token(self) -> _CachedToken:
        """POST client_credentials to CDSE and return the cached token."""
        logger.info("Requesting new CDSE access token")
        response = await self._client.post(
            self._settings.cdse_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._settings.cdse_client_id,
                "client_secret": self._settings.cdse_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        response.raise_for_status()
        payload = response.json()
        # CDSE returns "expires_in" in seconds (typically 600).
        expires_in = int(payload.get("expires_in", 600))
        return _CachedToken(
            access_token=payload["access_token"],
            expires_at=time.time() + expires_in,
        )