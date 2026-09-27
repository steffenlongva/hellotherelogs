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
      zone { name }
      guild { name }
      fights {
        id
        encounterID
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


FRIENDLY_DAMAGE_PAGE_QUERY = """
query HelloThereLogsFriendlyDamagePage($code: String!, $fightId: Int!, $sourceId: Int!, $startTime: Float!) {
  reportData {
    report(code: $code) {
      friendlyDamagePage: events(dataType: DamageDone, fightIDs: [$fightId], sourceID: $sourceId, startTime: $startTime, limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
    }
  }
}
"""

DEATH_DAMAGE_QUERY = """
query HelloThereLogsDeathDamage($code: String!, $fightId: Int!, $targetId: Int!, $startTime: Float!, $endTime: Float!) {
  reportData {
    report(code: $code) {
      deathDamage: events(dataType: DamageTaken, fightIDs: [$fightId], targetID: $targetId, startTime: $startTime, endTime: $endTime, limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
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
        cache_key = f"report:v1:{code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        data = await self.client.query(REPORT_QUERY, {"code": code})
        normalized = normalize_report(self._report_from_response(data))
        self.cache.set(cache_key, normalized)
        self.cache.set(f"fights:v1:{code}", normalized["fights"])
        return normalized

    async def get_fights(self, code: str) -> list[dict[str, Any]]:
        cache_key = f"fights:v1:{code}"
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
        death_damage = await self._death_damage_events(
            code, fight_id, fight["start_time_ms"], raw_report.get("deaths"), participant_ids
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
            },
            "events": {
                "deaths": raw_report.get("deaths"),
                "death_damage": death_damage,
                "interrupts": raw_report.get("interruptEvents"),
                "combatant_info": raw_report.get("combatantInfo"),
            },
            "player_details": raw_report.get("playerDetails"),
            "actors": participant_actors,
        }
        self.cache.set(cache_key, result)
        return result

    async def _death_damage_events(
        self, code: str, fight_id: int, fight_start: float, death_page: Any, participant_ids: set[int]
    ) -> list[dict[str, Any]]:
        if not isinstance(death_page, dict) or not isinstance(death_page.get("data"), list):
            return []
        recaps = []
        for death in death_page["data"]:
            if not isinstance(death, dict):
                continue
            target_id = death.get("targetID", death.get("targetId"))
            timestamp = death.get("timestamp")
            if target_id not in participant_ids or isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
                continue
            start_time = max(fight_start, timestamp - 8000)
            response = await self.client.query(DEATH_DAMAGE_QUERY, {
                "code": code,
                "fightId": fight_id,
                "targetId": target_id,
                "startTime": start_time,
                "endTime": timestamp,
            })
            report = self._report_from_response(response)
            page = report.get("deathDamage")
            events = page.get("data", []) if isinstance(page, dict) and isinstance(page.get("data"), list) else []
            page_count = 1
            while isinstance(page, dict) and page.get("nextPageTimestamp") is not None and page_count < 3:
                cursor = page["nextPageTimestamp"]
                next_response = await self.client.query(DEATH_DAMAGE_QUERY, {
                    "code": code,
                    "fightId": fight_id,
                    "targetId": target_id,
                    "startTime": cursor,
                    "endTime": timestamp,
                })
                next_report = self._report_from_response(next_response)
                next_page = next_report.get("deathDamage")
                if not isinstance(next_page, dict) or not isinstance(next_page.get("data"), list):
                    break
                events.extend(next_page["data"])
                page = next_page
                page_count += 1
            recaps.append({
                "target_id": target_id,
                "death_timestamp": timestamp,
                "window_start": start_time,
                "data": events,
                "complete": not (isinstance(page, dict) and page.get("nextPageTimestamp") is not None),
            })
        return recaps


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
