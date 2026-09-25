import json

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.report_samples import fresh_report


def make_settings(database_path) -> Settings:
    return Settings(
        wcl_client_id="test-client",
        wcl_client_secret="test-secret",
        database_url=f"sqlite:///{database_path}",
        cache_ttl_seconds=300,
    )


def api_transport(report_payload: dict | None, graphql_errors: bool = False, counts: dict | None = None):
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "test-access-token", "expires_in": 3600})
        if counts is not None:
            counts["graphql"] = counts.get("graphql", 0) + 1
        if graphql_errors:
            return httpx.Response(200, json={"errors": [{"message": "invalid query"}]})
        parsed = json.loads(request.content)
        assert "reportData" in parsed["query"]
        report = report_payload
        return httpx.Response(200, json={"data": {"reportData": {"report": report}}})
    return httpx.MockTransport(respond)


def test_parse_route_and_report_cache(tmp_path) -> None:
    counts: dict[str, int] = {}
    app = create_app(
        make_settings(tmp_path / "parse-cache.sqlite3"),
        http_transport=api_transport(fresh_report(), counts=counts),
    )
    with TestClient(app) as client:
        parsed = client.post("/api/reports/parse", json={"report_url": "https://fresh.warcraftlogs.com/reports/AbC123"})
        assert parsed.status_code == 200
        assert parsed.json() == {"report_code": "AbC123"}

        overview = client.get("/api/reports/AbC123")
        assert overview.status_code == 200
        assert overview.json()["fight_count"] == 3
        assert overview.json()["bosses"][0]["kills"] == 1

        # The fights endpoint shares the normalized fight cache populated by overview.
        fights = client.get("/api/reports/AbC123/fights")
        assert fights.status_code == 200
        assert len(fights.json()) == 3
        assert client.get("/api/reports/AbC123").status_code == 200
        assert counts["graphql"] == 1


def test_invalid_report_url_returns_422(tmp_path) -> None:
    app = create_app(make_settings(tmp_path / "bad-url.sqlite3"), http_transport=api_transport(fresh_report()))
    with TestClient(app) as client:
        response = client.post("/api/reports/parse", json={"report_url": "https://example.com/reports/AbC123"})
    assert response.status_code == 422


def test_graphql_errors_map_to_bad_gateway(tmp_path) -> None:
    app = create_app(
        make_settings(tmp_path / "api-error.sqlite3"),
        http_transport=api_transport(None, graphql_errors=True),
    )
    with TestClient(app) as client:
        response = client.get("/api/reports/AbC123")
    assert response.status_code == 502
    assert response.json()["detail"] == "Warcraft Logs could not provide a valid report response."


def test_missing_report_maps_to_not_found(tmp_path) -> None:
    app = create_app(
        make_settings(tmp_path / "not-found.sqlite3"),
        http_transport=api_transport(None),
    )
    with TestClient(app) as client:
        response = client.get("/api/reports/AbC123")
    assert response.status_code == 404
