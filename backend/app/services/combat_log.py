import csv
import io
import re
from collections import defaultdict
from typing import Any


MAX_LOG_BYTES = 160 * 1024 * 1024
TIMESTAMP = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}) (\d{2}:\d{2}:\d{2}\.\d+)")
ARMOR_REDUCTION = {
    "Sunder Armor": 520,
    "Expose Armor": 3075,
    "Faerie Fire": 610,
    "Faerie Fire (Feral)": 610,
    "Curse of Recklessness": 800,
}
STACKING_ARMOR_REDUCTION = {"Sunder Armor": 520}


def _timestamp(line: str) -> int | None:
    match = TIMESTAMP.match(line)
    if not match:
        return None
    from datetime import datetime

    try:
        return int(datetime.strptime(f"{match.group(1)} {match.group(2)}", "%m/%d/%Y %H:%M:%S.%f").timestamp() * 1000)
    except ValueError:
        return None


def analyze_combat_log(content: bytes) -> dict[str, Any]:
    if len(content) > MAX_LOG_BYTES:
        raise ValueError("Log file exceeds the 160 MB upload limit.")
    encounters: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_auras: dict[tuple[str, str, int, str, str], tuple[int, int]] = {}
    aura_totals: dict[tuple[str, str, int, str, str], int] = defaultdict(int)
    observed_stacks: dict[tuple[str, str, int, str, str], int] = defaultdict(lambda: 1)
    last_timestamp = 0
    line_count = 0

    for raw_line in io.BytesIO(content):
        line = raw_line.decode("utf-8", errors="replace").lstrip("\ufeff")
        line_count += 1
        timestamp = _timestamp(line)
        if timestamp is None:
            continue
        last_timestamp = timestamp
        try:
            fields = next(csv.reader([line[TIMESTAMP.match(line).end():].lstrip(" ,")]))
        except (csv.Error, StopIteration):
            continue
        if not fields:
            continue
        event = fields[0]
        if event == "ENCOUNTER_START" and len(fields) >= 3:
            current = {"id": fields[1], "name": fields[2], "start": timestamp, "end": None, "kill": None}
            encounters.append(current)
            pending_auras.clear()
            aura_totals.clear()
            observed_stacks.clear()
        elif current is not None and event == "ENCOUNTER_END":
            current["end"] = timestamp
            current["kill"] = fields[5] == "1" if len(fields) > 5 else None
            current["duration_seconds"] = round((timestamp - current["start"]) / 1000, 1)
            current["debuffs"] = _debuff_rows(aura_totals, current["start"], timestamp, pending_auras, observed_stacks)
            current["armor_reduction"] = _armor_rows(current["debuffs"])
            current = None
            pending_auras.clear()
            aura_totals.clear()
            observed_stacks.clear()
        elif current is not None and event.startswith("SPELL_AURA_") and len(fields) >= 13:
            source, target = fields[1], fields[5]
            source_name, target_name = fields[2], fields[6]
            try:
                spell_id = int(fields[9])
            except ValueError:
                spell_id = 0
            spell, aura_type = fields[10], fields[12]
            if aura_type != "DEBUFF":
                continue
            key = (target, target_name, spell_id, spell, source_name)
            change = event in ("SPELL_AURA_APPLIED", "SPELL_AURA_REFRESH", "SPELL_AURA_APPLIED_DOSE")
            if change:
                previous = pending_auras.get(key)
                if previous:
                    aura_totals[key] += max(0, timestamp - previous[0])
                stacks = 1
                if event == "SPELL_AURA_APPLIED_DOSE" and len(fields) > 13:
                    try:
                        stacks = int(fields[13])
                    except ValueError:
                        pass
                pending_auras[key] = (timestamp, stacks)
                observed_stacks[key] = max(observed_stacks[key], stacks)
                aura_totals.setdefault(key, 0)
                current.setdefault("providers", {})[key] = source_name
            elif "REMOVED_DOSE" in event:
                previous = pending_auras.get(key)
                if previous:
                    aura_totals[key] += max(0, timestamp - previous[0])
                    try:
                        pending_auras[key] = (timestamp, int(fields[13]))
                        observed_stacks[key] = max(observed_stacks[key], int(fields[13]))
                    except (IndexError, ValueError):
                        pending_auras.pop(key, None)
            elif "REMOVED" in event or "BROKEN" in event:
                previous = pending_auras.pop(key, None)
                if previous:
                    aura_totals[key] += max(0, timestamp - previous[0])

    if current is not None:
        current["end"] = last_timestamp
        current["kill"] = None
        current["duration_seconds"] = round(max(0, last_timestamp - current["start"]) / 1000, 1)
        current["debuffs"] = _debuff_rows(aura_totals, current["start"], last_timestamp, pending_auras, observed_stacks)
        current["armor_reduction"] = _armor_rows(current["debuffs"])
    for fight in encounters:
        if fight.get("end") and not fight.get("debuffs"):
            fight["debuffs"] = []
            fight["armor_reduction"] = []
        fight.pop("start", None)
        fight.pop("end", None)
        fight.pop("providers", None)
    if not encounters:
        raise ValueError("No ENCOUNTER_START events found. Upload a WoW advanced combat log.")
    return {"file_name": None, "encounters": encounters, "encounter_count": len(encounters), "line_count": line_count}


def _debuff_rows(totals: dict, start: int, end: int, pending: dict | None = None, observed_stacks: dict | None = None) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str, str, str], list[int]] = defaultdict(lambda: [0, 1])
    pending = pending or {}
    observed_stacks = observed_stacks or {}
    for key, elapsed in totals.items():
        target_id, target, spell_id, spell, provider = key
        active = pending.get(key)
        duration = elapsed + (max(0, end - active[0]) if active else 0)
        stacks = max(active[1] if active else 1, observed_stacks.get(key, 1))
        grouped[(spell_id, spell, target, provider)][0] += duration
        grouped[(spell_id, spell, target, provider)][1] = max(grouped[(spell_id, spell, target, provider)][1], stacks)
    rows = []
    for (spell_id, spell, target, provider), (uptime_ms, stacks) in grouped.items():
        rows.append({"spell_id": spell_id, "ability": spell, "target": target, "provider": provider,
                     "uptime_seconds": round(uptime_ms / 1000, 1), "uptime_percent": round(100 * uptime_ms / max(1, end - start), 1),
                     "armor_reduction": ARMOR_REDUCTION.get(spell, 0) or STACKING_ARMOR_REDUCTION.get(spell, 0) * stacks,
                     "armor_reduction_note": "estimated at the logged stack count" if spell in STACKING_ARMOR_REDUCTION else "estimated from the TBC spell rank"})
    return sorted(rows, key=lambda row: (-row["uptime_seconds"], row["ability"]))


def _armor_rows(debuffs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for row in debuffs:
        if not row["armor_reduction"]:
            continue
        item = totals.setdefault(row["ability"], {"ability": row["ability"], "estimated_armor_reduction": row["armor_reduction"], "uptime_seconds": 0.0, "targets": set()})
        item["uptime_seconds"] += row["uptime_seconds"]
        item["targets"].add(row["target"])
    return [{**item, "uptime_seconds": round(item["uptime_seconds"], 1), "targets": len(item["targets"])} for item in totals.values()]
