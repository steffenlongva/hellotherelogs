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
