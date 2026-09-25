import asyncio

import httpx

from app.core.config import Settings
from app.services.wcl_client import WCLClient


def test_oauth_token_is_cached_and_used_for_graphql() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "server-only", "expires_in": 3600})
        return httpx.Response(200, json={"data": {"rateLimitData": {"limitPerHour": 3600}}})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = WCLClient(
        Settings(wcl_client_id="client", wcl_client_secret="secret"), http=http
    )

    async def run_queries() -> dict:
        first = await client.query("{ rateLimitData { limitPerHour } }")
        second = await client.query("{ rateLimitData { limitPerHour } }")
        await http.aclose()
        return {"first": first, "second": second}

    result = asyncio.run(run_queries())
    assert result["first"] == result["second"]
    assert len(calls) == 3  # one token exchange and two GraphQL operations
    assert calls[0].url.path == "/oauth/token"
    assert calls[0].read().decode() == "grant_type=client_credentials"
    assert calls[1].headers["authorization"] == "Bearer server-only"
