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
      friendlyDamage: table(dataType: DamageDone, fightIDs: [$fightId], hostilityType: Friendlies, viewBy: Source)
      casts: table(dataType: Casts, fightIDs: [$fightId], viewBy: Source)
      deaths: events(dataType: Deaths, fightIDs: [$fightId], limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
      interrupts: table(dataType: Interrupts, fightIDs: [$fightId], viewBy: Source)
      buffUptimes: table(dataType: Buffs, fightIDs: [$fightId], viewBy: Target)
      interruptEvents: events(dataType: Interrupts, fightIDs: [$fightId], limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
      combatantInfo: events(dataType: CombatantInfo, fightIDs: [$fightId], limit: 10000, useActorIDs: true, useAbilityIDs: true) { data nextPageTimestamp }
      playerDetails: playerDetails(fightIDs: [$fightId], includeCombatantInfo: true)
    }
  }
}
"""


class ReportNotFoundError(LookupError):
    pass


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
        cache_key = f"analysis:v2:{code}:{fight_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        data = await self.client.query(FIGHT_ANALYSIS_QUERY, {"code": code, "fightId": fight_id})
        raw_report = self._report_from_response(data)
        participant_ids = set(fight.get("friendly_players") or [])
        all_actors = (raw_report.get("masterData") or {}).get("actors", [])
        participants = [
            actor for actor in all_actors
            if isinstance(actor, dict)
            and actor.get("type") == "Player"
            and actor.get("id") in participant_ids
        ]
        result = {
            "fight": fight,
            "tables": {
                "damage": raw_report.get("damage"),
                "healing": raw_report.get("healing"),
                "damage_taken": raw_report.get("damageTaken"),
                "friendly_damage": raw_report.get("friendlyDamage"),
                "casts": raw_report.get("casts"),
                "deaths": raw_report.get("deaths"),
                "interrupts": raw_report.get("interrupts"),
                "buff_uptimes": raw_report.get("buffUptimes"),
            },
            "events": {
                "deaths": raw_report.get("deaths"),
                "interrupts": raw_report.get("interruptEvents"),
                "combatant_info": raw_report.get("combatantInfo"),
            },
            "player_details": raw_report.get("playerDetails"),
            "actors": participants,
        }
        self.cache.set(cache_key, result)
        return result
