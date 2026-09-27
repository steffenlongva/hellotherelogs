from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any


class ReportNormalizationError(ValueError):
    pass


def _required_number(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReportNormalizationError(f"Warcraft Logs report is missing numeric {key}.")
    return float(value)


def _iso_utc(milliseconds: float) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_fight(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        fight_id = raw["id"]
        encounter_id = raw["encounterID"]
        name = raw["name"]
        start_time = float(raw["startTime"])
        end_time = float(raw["endTime"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReportNormalizationError("Warcraft Logs returned an incomplete fight.") from exc
    if not isinstance(fight_id, int) or not isinstance(encounter_id, int) or not isinstance(name, str):
        raise ReportNormalizationError("Warcraft Logs returned invalid fight fields.")
    return {
        "fight_id": fight_id,
        "encounter_id": encounter_id,
        "difficulty": raw.get("difficulty") if isinstance(raw.get("difficulty"), int) else None,
        "name": name,
        "start_time_ms": start_time,
        "end_time_ms": end_time,
        "duration_ms": max(0.0, end_time - start_time),
        "kill": raw.get("kill"),
        "fight_percentage": raw.get("fightPercentage"),
        "friendly_players": raw.get("friendlyPlayers") or [],
    }


def normalize_report(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert the documented Fresh Report and ReportFight fields to app DTOs."""
    try:
        code = raw["code"]
        title = raw["title"]
    except (KeyError, TypeError) as exc:
        raise ReportNormalizationError("Warcraft Logs returned an incomplete report.") from exc
    if not isinstance(code, str) or not isinstance(title, str):
        raise ReportNormalizationError("Warcraft Logs returned invalid report fields.")

    start_time = _required_number(raw, "startTime")
    end_time = _required_number(raw, "endTime")
    fights = [normalize_fight(fight) for fight in (raw.get("fights") or [])]
    bosses: OrderedDict[int, dict[str, Any]] = OrderedDict()
    for fight in fights:
        encounter_id = fight["encounter_id"]
        if encounter_id == 0:
            continue
        boss = bosses.setdefault(encounter_id, {
            "encounter_id": encounter_id,
            "name": fight["name"],
            "attempts": 0,
            "kills": 0,
            "wipes": 0,
            "fights": [],
        })
        boss["attempts"] += 1
        if fight["kill"] is True:
            boss["kills"] += 1
        elif fight["kill"] is False:
            boss["wipes"] += 1
        boss["fights"].append(fight)

    guild = raw.get("guild")
    zone = raw.get("zone")
    return {
        "code": code,
        "title": title,
        "zone": zone.get("name") if isinstance(zone, dict) else None,
        "zone_id": zone.get("id") if isinstance(zone, dict) and isinstance(zone.get("id"), int) else None,
        "guild": guild.get("name") if isinstance(guild, dict) else None,
        "start_time": _iso_utc(start_time),
        "end_time": _iso_utc(end_time),
        "duration_ms": max(0.0, end_time - start_time),
        "fight_count": len(fights),
        "boss_count": len(bosses),
        "kill_count": sum(boss["kills"] for boss in bosses.values()),
        "wipe_count": sum(boss["wipes"] for boss in bosses.values()),
        "bosses": list(bosses.values()),
        "fights": fights,
    }
