"""Minimal server-side Warcraft Logs OAuth and GraphQL transport."""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class WCLConfigurationError(RuntimeError):
    pass


class WCLAPIError(RuntimeError):
    pass


class WCLClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self.http = http or httpx.AsyncClient(timeout=30.0)
        self._owns_http = http is None
        self._token: str | None = None
        self._token_expiry = 0.0
        self._token_lock = asyncio.Lock()

    async def _access_token(self) -> str:
        if not self.settings.wcl_client_id or not self.settings.wcl_client_secret:
            raise WCLConfigurationError("Set WCL_CLIENT_ID and WCL_CLIENT_SECRET on the backend.")
        async with self._token_lock:
            if self._token and time.monotonic() < self._token_expiry - 30:
                return self._token
            response = await self.http.post(
                self.settings.wcl_token_url,
                data={"grant_type": "client_credentials"},
                auth=(self.settings.wcl_client_id, self.settings.wcl_client_secret),
            )
            if response.is_error:
                logger.error("Warcraft Logs token request failed with HTTP %s.", response.status_code)
                raise WCLAPIError(f"Warcraft Logs token request failed ({response.status_code}).")
            payload = response.json()
            self._token = payload["access_token"]
            self._token_expiry = time.monotonic() + float(payload.get("expires_in", 3600))
            return self._token

    async def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self._access_token()
        response = await self.http.post(
            self.settings.wcl_graphql_url,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.is_error:
            logger.error("Warcraft Logs GraphQL request failed with HTTP %s.", response.status_code)
            raise WCLAPIError(f"Warcraft Logs GraphQL request failed ({response.status_code}).")
        payload = response.json()
        if payload.get("errors"):
            messages = [
                str(error.get("message", "Unknown GraphQL error"))
                for error in payload["errors"]
                if isinstance(error, dict)
            ]
            logger.error("Warcraft Logs GraphQL errors: %s", "; ".join(messages)[:1000])
            raise WCLAPIError("Warcraft Logs returned a GraphQL error: " + "; ".join(messages)[:500])
        return payload.get("data", {})

    async def close(self) -> None:
        if self._owns_http:
            await self.http.aclose()
