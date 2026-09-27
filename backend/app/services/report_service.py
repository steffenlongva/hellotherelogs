import json
from typing import Any

from app.services.report_normalizer import normalize_fight, normalize_report
from app.services.sqlite_cache import SQLiteCache
from app.services.wcl_client import WCLClient


REPORT_QUERY = """
query HelloThereLogsReport($code: String!) {
  reportData {
    report(code: $code) {
      code
      title
      startTime
      endTime
      zone { id name }
      guild { name }
      fights {
        id
        encounterID
        difficulty
        name
        startTime
        endTime
        kill
        fightPercentage
        friendlyPlayers
      }
    }
  }
}
"""

REPORT_FIGHTS_QUERY = """
query HelloThereLogsReportFights($code: String!) {
  reportData {
    report(code: $code) {
      code
      fights {
        id
        encounterID
        difficulty
        name
        startTime
        endTime
        kill
        fightPercentage
        friendlyPlayers
      }
    }
  }
}
"""

FIGHT_ANALYSIS_QUERY = """
query HelloThereLogsFightAnalysis($code: String!, $fightId: Int!) {
  reportData {
    report(code: $code) {
      code
      fights { id name encounterID startTime endTime kill }
      masterData { actors { id name type subType petOwner } }
      damage: table(dataType: DamageDone, fightIDs: [$fightId], viewBy: Source)
      healing: table(dataType: Healing, fightIDs: [$fightId], viewBy: Source)
      damageTaken: table(dataType: DamageTaken, fightIDs: [$fightId], viewBy: Target)
      casts: table(dataType: Casts, fightIDs: [$fightId], viewBy: Source)
      deaths: events(dataType: Deaths, fightIDs: [$fightId], limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
      interrupts: table(dataType: Interrupts, fightIDs: [$fightId], viewBy: Source)
      buffUptimes: table(dataType: Buffs, fightIDs: [$fightId], viewBy: Target)
      abilityUptimes: table(dataType: Buffs, fightIDs: [$fightId], viewBy: Ability)
      debuffUptimes: table(dataType: Debuffs, fightIDs: [$fightId], viewBy: Ability)
      interruptEvents: events(dataType: Interrupts, fightIDs: [$fightId], limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
      combatantInfo: events(dataType: CombatantInfo, fightIDs: [$fightId], limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
      playerDetails: playerDetails(fightIDs: [$fightId], includeCombatantInfo: true)
      __FRIENDLY_DAMAGE_EVENT_FIELDS__
    }
  }
}
"""


class ReportNotFoundError(LookupError):
    pass


def _unavailable_benchmarks(fight: dict[str, Any], strictness: str, reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "encounter": fight.get("name"),
        "strictness": strictness,
        "source": "Warcraft Logs execution leaderboard",
        "sample_size": 0,
        "match_basis": [],
        "limitations": [reason],
        "candidates": [],
    }


def _ranking_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    found: list[dict[str, Any]] = []
    visited: set[int] = set()

    def visit(node: Any, depth: int = 0) -> None:
        if depth > 9 or id(node) in visited:
            return
        if isinstance(node, (dict, list)):
            visited.add(id(node))
        if isinstance(node, list):
            for item in node:
                visit(item, depth + 1)
        elif isinstance(node, dict):
            report = node.get("report")
            code = node.get("reportCode") or (report.get("code") if isinstance(report, dict) else None)
            if isinstance(code, str) and code:
                found.append(node)
            else:
                for item in node.values():
                    visit(item, depth + 1)

    visit(value)
    return found


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    records: list[dict[str, Any]] = []
    def visit(node: Any, depth: int = 0) -> None:
        if depth > 10:
            return
        if isinstance(node, dict):
            records.append(node)
            for item in node.values():
                visit(item, depth + 1)
        elif isinstance(node, list):
            for item in node:
                visit(item, depth + 1)
    visit(value)
    return records


def _class_counts(value: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in _records(value):
        if record.get("type") not in (None, "Player"):
            continue
        class_name = record.get("subType") or record.get("className") or record.get("class")
        if isinstance(class_name, dict):
            class_name = class_name.get("name")
        if isinstance(class_name, str) and class_name:
            counts[class_name] = counts.get(class_name, 0) + 1
    return counts


def _average_item_level(value: Any) -> float | None:
    records = _records(value)
    summaries = [
        record.get(key)
        for record in records
        for key in ("averageItemLevel", "averageItemLevelEquipped", "avgItemLevel", "ilvl")
        if isinstance(record.get(key), (int, float)) and not isinstance(record.get(key), bool)
    ]
    values = summaries
    if not values:
        values = [
            record.get("itemLevel", record.get("ilvl"))
            for record in records
            if isinstance(record.get("itemLevel", record.get("ilvl")), (int, float))
            and not isinstance(record.get("itemLevel", record.get("ilvl")), bool)
        ]
    return sum(values) / len(values) if values else None


def _ranking_candidate(row: dict[str, Any]) -> dict[str, Any] | None:
    report = row.get("report") if isinstance(row.get("report"), dict) else {}
    code = row.get("reportCode") or report.get("code")
    fight_id = row.get("fightID", row.get("fightId", report.get("fightID", report.get("fightId"))))
    if not isinstance(code, str) or not code.isalnum() or not isinstance(fight_id, int):
        return None
    duration = next((row.get(key) for key in ("duration", "durationMS", "durationMs", "fightDuration") if isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool)), None)
    if duration is not None:
        duration = float(duration) / (1000 if duration > 10000 else 1)
    guild = row.get("guild")
    if isinstance(guild, dict):
        guild = guild.get("name")
    return {
        "report_code": code,
        "fight_id": fight_id,
        "title": row.get("title") or report.get("title"),
        "guild": guild if isinstance(guild, str) else None,
        "duration_seconds": duration,
        "rank_percent": row.get("rankPercent", row.get("rankPercentile")),
        "composition_similarity": None,
        "average_item_level": None,
        "item_level_difference": None,
        "url": f"https://fresh.warcraftlogs.com/reports/{code}#fight={fight_id}",
    }


FRIENDLY_DAMAGE_PAGE_QUERY = """
query HelloThereLogsFriendlyDamagePage($code: String!, $fightId: Int!, $sourceId: Int!, $startTime: Float!) {
  reportData {
    report(code: $code) {
      friendlyDamagePage: events(dataType: DamageDone, fightIDs: [$fightId], sourceID: $sourceId, startTime: $startTime, limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
    }
  }
}
"""

ENCOUNTER_RANKINGS_QUERY = """
query HelloThereLogsEncounterBenchmarks($encounterId: Int!, $difficulty: Int!, $size: Int!) {
  worldData {
    encounter(id: $encounterId) {
      id
      name
      fightRankings(difficulty: $difficulty, size: $size, metric: Execution, includeOtherPlayers: true)
    }
  }
}
"""


class ReportService:
    def __init__(self, client: WCLClient, cache: SQLiteCache):
        self.client = client
        self.cache = cache

    @staticmethod
    def _report_from_response(data: dict[str, Any]) -> dict[str, Any]:
        report_data = data.get("reportData")
        report = report_data.get("report") if isinstance(report_data, dict) else None
        if not isinstance(report, dict):
            raise ReportNotFoundError("Report was not found or is not publicly accessible.")
        return report

    async def get_report(self, code: str) -> dict[str, Any]:
        cache_key = f"report:v2:{code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        data = await self.client.query(REPORT_QUERY, {"code": code})
        normalized = normalize_report(self._report_from_response(data))
        self.cache.set(cache_key, normalized)
        self.cache.set(f"fights:v2:{code}", normalized["fights"])
        return normalized

    async def get_fights(self, code: str) -> list[dict[str, Any]]:
        cache_key = f"fights:v2:{code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        data = await self.client.query(REPORT_FIGHTS_QUERY, {"code": code})
        report = self._report_from_response(data)
        fights = [normalize_fight(fight) for fight in (report.get("fights") or [])]
        self.cache.set(cache_key, fights)
        return fights

    async def get_fight_analysis(self, code: str, fight_id: int) -> dict[str, Any]:
        report = await self.get_report(code)
        fight = next((item for item in report["fights"] if item["fight_id"] == fight_id), None)
        if fight is None:
            raise ReportNotFoundError("Fight was not found in this report.")
        cache_key = f"analysis:v4:{code}:{fight_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        participant_ids = set(fight.get("friendly_players") or [])
        player_ids = sorted(player_id for player_id in participant_ids if isinstance(player_id, int) and not isinstance(player_id, bool))
        friendly_fields = "\n".join(
            f"friendlyDamage{index}: events(dataType: DamageDone, fightIDs: [$fightId], sourceID: {player_id}, limit: 10000, useActorIDs: true, useAbilityIDs: true) {{ data nextPageTimestamp }}"
            for index, player_id in enumerate(player_ids)
        ) or "__typename"
        analysis_query = FIGHT_ANALYSIS_QUERY.replace("__FRIENDLY_DAMAGE_EVENT_FIELDS__", friendly_fields)
        data = await self.client.query(analysis_query, {"code": code, "fightId": fight_id})
        raw_report = self._report_from_response(data)
        all_actors = (raw_report.get("masterData") or {}).get("actors", [])
        participant_actors = [
            actor for actor in all_actors
            if isinstance(actor, dict)
            and actor.get("type") == "Player"
            and actor.get("id") in participant_ids
        ]
        source_event_data = {player_id: raw_report.get(f"friendlyDamage{index}") for index, player_id in enumerate(player_ids)}
        for player_id, first_page in source_event_data.items():
            page = first_page
            page_count = 1
            while isinstance(page, dict) and page.get("nextPageTimestamp") is not None and page_count < 6:
                cursor = page["nextPageTimestamp"]
                next_data = await self.client.query(
                    FRIENDLY_DAMAGE_PAGE_QUERY,
                    {"code": code, "fightId": fight_id, "sourceId": player_id, "startTime": cursor},
                )
                next_report = self._report_from_response(next_data)
                next_page = next_report.get("friendlyDamagePage")
                if not isinstance(next_page, dict) or not isinstance(next_page.get("data"), list):
                    page["nextPageTimestamp"] = cursor
                    break
                previous_events = page.get("data") if isinstance(page.get("data"), list) else []
                source_event_data[player_id] = {
                    "data": previous_events + next_page["data"],
                    "nextPageTimestamp": next_page.get("nextPageTimestamp"),
                }
                page = source_event_data[player_id]
                page_count += 1
        friendly_damage, friendly_damage_abilities, friendly_damage_complete = _friendly_damage_by_player(
            source_event_data, participant_ids
        )
        result = {
            "fight": fight,
            "tables": {
                "damage": raw_report.get("damage"),
                "healing": raw_report.get("healing"),
                "damage_taken": raw_report.get("damageTaken"),
                "friendly_damage": friendly_damage,
                "friendly_damage_abilities": friendly_damage_abilities,
                "friendly_damage_complete": friendly_damage_complete,
                "casts": raw_report.get("casts"),
                "deaths": raw_report.get("deaths"),
                "interrupts": raw_report.get("interrupts"),
                "buff_uptimes": raw_report.get("buffUptimes"),
                "ability_uptimes": raw_report.get("abilityUptimes"),
                "debuff_uptimes": raw_report.get("debuffUptimes"),
            },
            "events": {
                "deaths": raw_report.get("deaths"),
                "interrupts": raw_report.get("interruptEvents"),
                "combatant_info": raw_report.get("combatantInfo"),
            },
            "player_details": raw_report.get("playerDetails"),
            "actors": participant_actors,
        }
        self.cache.set(cache_key, result)
        return result

    async def get_benchmarks(self, code: str, fight_id: int, strictness: str = "balanced") -> dict[str, Any]:
        """Return public encounter logs matched by raid size and pull duration."""
        if strictness not in {"strict", "balanced", "broad"}:
            raise ValueError("Benchmark strictness must be strict, balanced, or broad.")
        report = await self.get_report(code)
        fight = next((item for item in report["fights"] if item["fight_id"] == fight_id), None)
        if fight is None:
            raise ReportNotFoundError("Fight was not found in this report.")
        difficulty = fight.get("difficulty")
        roster_size = len(fight.get("friendly_players") or [])
        if fight["encounter_id"] <= 0 or not isinstance(difficulty, int) or roster_size <= 0:
            return _unavailable_benchmarks(fight, strictness, "This pull is missing encounter, difficulty, or roster-size data.")

        cache_key = f"benchmarks:v1:{code}:{fight_id}:{strictness}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        data = await self.client.query(ENCOUNTER_RANKINGS_QUERY, {
            "encounterId": fight["encounter_id"],
            "difficulty": difficulty,
            "size": roster_size,
        })
        world_data = data.get("worldData")
        encounter = world_data.get("encounter") if isinstance(world_data, dict) else None
        if not isinstance(encounter, dict):
            return _unavailable_benchmarks(fight, strictness, "Warcraft Logs returned no encounter leaderboard for this pull.")
        ranking_data = encounter.get("fightRankings")
        rows = _ranking_rows(ranking_data)
        duration_seconds = fight["duration_ms"] / 1000
        duration_tolerance = {"strict": 0.10, "balanced": 0.20, "broad": None}[strictness]
        analysis = await self.get_fight_analysis(code, fight_id)
        target_classes = _class_counts(analysis.get("actors", []))
        target_ilvl = _average_item_level(analysis.get("player_details"))
        composition_floor = {"strict": 0.80, "balanced": 0.60, "broad": None}[strictness]
        item_level_tolerance = {"strict": 3.0, "balanced": 6.0, "broad": None}[strictness]
        candidates = []
        for row in rows:
            candidate = _ranking_candidate(row)
            if candidate is None:
                continue
            if duration_tolerance is not None and candidate["duration_seconds"] is None:
                continue
            if duration_tolerance is not None:
                difference = abs(candidate["duration_seconds"] - duration_seconds) / max(1, duration_seconds)
                if difference > duration_tolerance:
                    continue
            candidate_classes = _class_counts(row)
            if composition_floor is not None and target_classes and not candidate_classes:
                continue
            if composition_floor is not None and target_classes and candidate_classes:
                overlap = sum(min(count, candidate_classes.get(name, 0)) for name, count in target_classes.items())
                similarity = overlap / max(1, sum(target_classes.values()))
                if similarity < composition_floor:
                    continue
                candidate["composition_similarity"] = round(similarity, 3)
            candidate_ilvl = _average_item_level(row)
            if item_level_tolerance is not None and target_ilvl is not None and candidate_ilvl is None:
                continue
            if candidate_ilvl is not None:
                candidate["average_item_level"] = round(candidate_ilvl, 1)
                if target_ilvl is not None:
                    item_level_difference = candidate_ilvl - target_ilvl
                    if item_level_tolerance is not None and abs(item_level_difference) > item_level_tolerance:
                        continue
                    candidate["item_level_difference"] = round(item_level_difference, 1)
            candidates.append(candidate)
        candidates = candidates[:50]
        result = {
            "status": "available" if candidates else "empty",
            "encounter": encounter.get("name") or fight["name"],
            "strictness": strictness,
            "source": "Warcraft Logs execution leaderboard",
            "sample_size": len(candidates),
            "match_basis": [
                "same encounter",
                "same difficulty",
                f"same raid size ({roster_size})",
                "kill leaderboard records",
                f"pull duration within {int(duration_tolerance * 100)}%" if duration_tolerance is not None else "duration not filtered",
                f"class composition overlap ≥ {int(composition_floor * 100)}% when WCL returns it" if composition_floor is not None else "class composition not filtered",
                f"average item level within ±{item_level_tolerance:.0f} when WCL returns it" if item_level_tolerance is not None else "item level not filtered",
            ],
            "limitations": [
                "The public leaderboard is execution-ranked and may favor exceptional logs over typical raid performance.",
                "Player specialization is not consistently present in the public fight leaderboard response.",
                "Composition and item level filters are applied only when Warcraft Logs includes those fields; otherwise they are shown as unavailable.",
                "This is a reference cohort, not a player grade; assignments and encounter context still matter.",
            ],
            "candidates": candidates,
        }
        self.cache.set(cache_key, result)
        return result


def _friendly_damage_by_player(
    source_events: dict[int, Any], participant_ids: set[int]
) -> tuple[dict[int, int], dict[int, list[dict[str, Any]]], bool]:
    totals: dict[int, int] = {}
    by_ability: dict[int, list[dict[str, Any]]] = {}
    complete = True
    for source_id, page in source_events.items():
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            complete = False
            continue
        totals[source_id] = 0
        by_ability[source_id] = []
        if page.get("nextPageTimestamp") is not None:
            complete = False
        for event in page["data"]:
            if not isinstance(event, dict):
                continue
            target_id = event.get("targetID", event.get("targetId"))
            amount = event.get("amount")
            if target_id not in participant_ids or isinstance(amount, bool) or not isinstance(amount, (int, float)):
                continue
            damage = int(amount)
            totals[source_id] = totals.get(source_id, 0) + damage
            ability = event.get("ability") if isinstance(event.get("ability"), dict) else {}
            ability_id = ability.get("guid", ability.get("id"))
            ability_name = ability.get("name", "Unknown ability")
            existing = next((row for row in by_ability.setdefault(source_id, []) if row["id"] == ability_id), None)
            if existing is None:
                by_ability[source_id].append({"id": ability_id, "name": ability_name, "amount": damage, "hits": 1})
            else:
                existing["amount"] += damage
                existing["hits"] += 1
    return totals, by_ability, complete
