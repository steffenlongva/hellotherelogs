import asyncio
import json
from typing import Any

from app.services.report_service import (
    BENCHMARK_REPORT_QUERY,
    ENCOUNTER_RANKINGS_QUERY,
    FIGHT_ANALYSIS_QUERY,
    REPORT_QUERY,
    ReportService,
    _actor_specs,
    _average_item_level,
    _class_counts,
    _ranking_candidate,
    _ranking_rows,
)


class MemoryCache:
    def __init__(self):
        self.values: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self.values.get(key)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value


class BenchmarkClient:
    def __init__(self):
        self.peer_reports = {
            ("PeerA123", 10): _peer_report(10, "Warrior", "Priest", 70),
            ("PeerB123", 20): _peer_report(20, "Mage", "Druid", 82),
        }

    async def query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        if query == REPORT_QUERY:
            return {"reportData": {"report": _selected_report()}}
        if query.lstrip().startswith("query HelloThereLogsFightAnalysis"):
            return {"reportData": {"report": {
                "fights": [_selected_report()["fights"][0]],
                "masterData": {"actors": _actors("Warrior", "Priest")},
                "friendlyDamage0": {"data": [], "nextPageTimestamp": None},
                "friendlyDamage1": {"data": [], "nextPageTimestamp": None},
                "playerDetails": {"players": [
                    {"id": 11, "name": "Player One", "spec": "Fury", "server": {"slug": "realm-one", "region": {"compactName": "US"}}},
                    {"id": 12, "name": "Player Two", "spec": "Holy", "server": {"slug": "realm-two", "region": {"compactName": "EU"}}},
                ]},
            }}}
        if query == ENCOUNTER_RANKINGS_QUERY:
            return {"worldData": {"encounter": {"name": "Test Boss", "fightRankings": json.dumps({"rankings": [
                {"report": {"code": "PeerA123", "fightID": 10}, "duration": 60, "guild": "Peer A", "rankPercent": 92},
                {"report": {"code": "PeerB123", "fightID": 20}, "duration": 60, "guild": "Peer B", "rankPercent": 88},
            ]})}}}
        if query.lstrip().startswith("query HelloThereLogsRecentPeerRankings"):
            return {"characterData": {
                "player0": {"encounterRankings": {"rankings": [{"report": {"code": "PeerA123", "fightID": 10}, "rankPercent": 92}]}},
                "player1": {"encounterRankings": {"rankings": [{"report": {"code": "PeerA123", "fightID": 10}, "rankPercent": 88}]}},
            }}
        if query == BENCHMARK_REPORT_QUERY:
            code = variables["code"]
            fight_id = variables["fightId"]
            return {"reportData": {"report": self.peer_reports[(code, fight_id)]}}
        raise AssertionError(f"Unexpected query: {query[:80]}")


def _actors(first_class: str, second_class: str) -> list[dict[str, Any]]:
    return [
        {"id": 11, "name": "Player One", "type": "Player", "subType": first_class},
        {"id": 12, "name": "Player Two", "type": "Player", "subType": second_class},
    ]


def _fight(fight_id: int, first_class: str, second_class: str, average_item_level: float) -> dict[str, Any]:
    return {
        "id": fight_id,
        "encounterID": 100,
        "difficulty": 3,
        "name": "Test Boss",
        "startTime": 10_000,
        "endTime": 70_000,
        "kill": True,
        "averageItemLevel": average_item_level,
        "friendlyPlayers": [11, 12],
    }


def _selected_report() -> dict[str, Any]:
    return {
        "code": "Guild123",
        "title": "Guild report",
        "startTime": 1_700_000_000_000,
        "endTime": 1_700_000_060_000,
        "zone": {"id": 10, "name": "Test Zone"},
        "fights": [_fight(1, "Warrior", "Priest", 70)],
    }


def _peer_report(fight_id: int, first_class: str, second_class: str, average_item_level: float) -> dict[str, Any]:
    return {
        "code": f"Peer{fight_id}",
        "title": "Reference kill",
        "fights": [_fight(fight_id, first_class, second_class, average_item_level)],
        "masterData": {"actors": _actors(first_class, second_class)},
        "damage": {"data": {"entries": []}},
        "healing": {"data": {"entries": []}},
        "damageTaken": {"data": {"entries": []}},
        "casts": {"data": {"entries": []}},
        "interrupts": {"data": {"entries": []}},
        "buffUptimes": {"data": {"entries": []}},
        "abilityUptimes": {"data": {"entries": []}},
        "debuffUptimes": {"data": {"entries": []}},
        "deaths": {"data": [], "nextPageTimestamp": None},
        "interruptEvents": {"data": [], "nextPageTimestamp": None},
        "playerDetails": {"players": [
            {"id": 11, "spec": "Fury"},
            {"id": 12, "spec": "Holy"},
        ]},
    }


def test_ranking_helpers_extract_public_fight_metadata() -> None:
    ranking = {"report": {"code": "PeerA123", "fightID": 4}, "duration": 90_000, "rankPercent": 85}
    rows = _ranking_rows(json.dumps({"rankings": [ranking]}))

    assert rows == [ranking]
    assert _ranking_candidate(ranking) == {
        "report_code": "PeerA123",
        "fight_id": 4,
        "title": None,
        "guild": None,
        "duration_seconds": 90,
        "rank_percent": 85,
        "composition_similarity": None,
        "average_item_level": None,
        "item_level_difference": None,
        "url": "https://fresh.warcraftlogs.com/reports/PeerA123#fight=4",
    }


def test_benchmark_helpers_use_actor_class_and_item_data() -> None:
    participants = [
        {"type": "Player", "subType": "Warrior"},
        {"type": "Player", "subType": "Priest"},
    ]
    details = {"players": [{"id": 11, "spec": "Fury", "gear": [{"itemLevel": 70}]}]}

    assert _class_counts(participants) == {"Warrior": 1, "Priest": 1}
    assert _average_item_level(details) == 70
    assert _actor_specs(details) == {11: "Fury"}


def test_recent_peer_sources_require_actor_spec_and_server_identity() -> None:
    from app.services.report_service import _recent_player_sources

    details = {"players": [
        {"id": 11, "name": "Player One", "spec": "Fury", "server": {"slug": "realm-one", "region": {"compactName": "US"}}},
        {"id": 12, "name": "Player Two", "spec": "Holy", "server": {"slug": "realm-two", "region": {"compactName": "EU"}}},
        {"id": 99, "name": "Outsider", "spec": "Fury", "server": "realm-three", "region": "US"},
    ]}

    assert _recent_player_sources(details, {11, 12}) == [
        {"actor_id": "11", "name": "Player One", "spec": "Fury", "server_slug": "realm-one", "server_region": "US"},
        {"actor_id": "12", "name": "Player Two", "spec": "Holy", "server_slug": "realm-two", "server_region": "EU"},
    ]


def test_get_benchmarks_filters_and_returns_reference_reports() -> None:
    service = ReportService(BenchmarkClient(), MemoryCache())  # type: ignore[arg-type]

    result = asyncio.run(service.get_benchmarks("Guild123", 1, "strict"))

    assert result["status"] == "available"
    assert result["sample_size"] == 1
    assert result["candidates"][0]["report_code"] == "PeerA123"
    assert result["candidates"][0]["composition_similarity"] == 1
    assert result["candidates"][0]["average_item_level"] == 70
    assert result["reference_analyses"][0]["player_specs"] == {"11": "Fury", "12": "Holy"}
    assert result["reference_analyses"][0]["tables"]["casts"] == {"data": {"entries": []}}
    assert "average item level within ±3" in result["match_basis"]


def test_recent_peer_benchmarks_use_roster_rankings() -> None:
    service = ReportService(BenchmarkClient(), MemoryCache())  # type: ignore[arg-type]

    result = asyncio.run(service.get_benchmarks("Guild123", 1, "strict", "recent"))

    assert result["cohort_source"] == "recent"
    assert result["source"] == "Warcraft Logs recent two-week spec parses"
    assert result["sample_size"] == 1
    assert result["candidates"][0]["matched_specs"] == ["Fury", "Holy"]


def test_benchmark_searches_past_first_five_nonmatching_reports() -> None:
    class LateMatchClient(BenchmarkClient):
        def __init__(self):
            super().__init__()
            for index in range(5):
                fight_id = 30 + index
                self.peer_reports[(f"PeerBad{index}", fight_id)] = _peer_report(fight_id, "Mage", "Druid", 82)

        async def query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
            if query == ENCOUNTER_RANKINGS_QUERY:
                rankings = [
                    {"report": {"code": f"PeerBad{index}", "fightID": 30 + index}, "duration": 60}
                    for index in range(5)
                ]
                rankings.append({"report": {"code": "PeerA123", "fightID": 10}, "duration": 60, "rankPercent": 92})
                return {"worldData": {"encounter": {"name": "Test Boss", "fightRankings": json.dumps({"rankings": rankings})}}}
            return await super().query(query, variables)

    service = ReportService(LateMatchClient(), MemoryCache())  # type: ignore[arg-type]

    result = asyncio.run(service.get_benchmarks("Guild123", 1, "strict", "execution"))

    assert result["sample_size"] == 1
    assert result["candidates"][0]["report_code"] == "PeerA123"


def test_benchmark_does_not_compare_wipes_with_completed_kills() -> None:
    class WipeClient(BenchmarkClient):
        async def query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
            if query == REPORT_QUERY:
                report = _selected_report()
                report["fights"][0]["kill"] = False
                return {"reportData": {"report": report}}
            if query == ENCOUNTER_RANKINGS_QUERY:
                raise AssertionError("A wipe should not query kill rankings")
            return await super().query(query, variables)

    service = ReportService(WipeClient(), MemoryCache())  # type: ignore[arg-type]

    result = asyncio.run(service.get_benchmarks("Guild123", 1, "balanced", "execution"))

    assert result["status"] == "unavailable"
    assert "completed kills" in result["limitations"][0]
