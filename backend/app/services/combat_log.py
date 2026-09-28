import csv
import gzip
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
LONG_BUFF_FAMILIES = {
    "Arcane Intellect": ("arcane intellect", "arcane brilliance"),
    "Power Word: Fortitude": ("power word: fortitude", "prayer of fortitude"),
    "Mark of the Wild": ("mark of the wild", "gift of the wild"),
    "Blessing of Kings": ("blessing of kings", "greater blessing of kings"),
    "Blessing of Might": ("blessing of might", "greater blessing of might"),
    "Blessing of Wisdom": ("blessing of wisdom", "greater blessing of wisdom"),
    "Blessing of Salvation": ("blessing of salvation", "greater blessing of salvation"),
    "Blessing of Sanctuary": ("blessing of sanctuary", "greater blessing of sanctuary"),
    "Divine Spirit": ("divine spirit", "prayer of spirit"),
    "Shadow Protection": ("shadow protection", "prayer of shadow protection"),
}


def decompress_combat_log(content: bytes) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as compressed:
            expanded = compressed.read(MAX_LOG_BYTES + 1)
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise ValueError("The compressed combat log is invalid or incomplete.") from exc
    if len(expanded) > MAX_LOG_BYTES:
        raise ValueError("Log file exceeds the 160 MB uncompressed upload limit.")
    return expanded


def _timestamp(line: str) -> int | None:
    match = TIMESTAMP.match(line)
    if not match:
        return None
    from datetime import datetime

    try:
        return int(datetime.strptime(f"{match.group(1)} {match.group(2)}", "%m/%d/%Y %H:%M:%S.%f").timestamp() * 1000)
    except ValueError:
        return None


def _long_buff_family(name: str) -> str | None:
    lowered = name.casefold()
    return next((family for family, aliases in LONG_BUFF_FAMILIES.items() if any(alias in lowered for alias in aliases)), None)


def analyze_combat_log(content: bytes) -> dict[str, Any]:
    if len(content) > MAX_LOG_BYTES:
        raise ValueError("Log file exceeds the 160 MB upload limit.")
    encounters: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_auras: dict[tuple[Any, ...], tuple[int, int]] = {}
    aura_totals: dict[tuple[Any, ...], int] = defaultdict(int)
    observed_stacks: dict[tuple[Any, ...], int] = defaultdict(lambda: 1)
    aura_applications: dict[tuple[Any, ...], int] = defaultdict(int)
    long_buff_intervals: list[dict[str, Any]] = []
    active_long_buffs: dict[tuple[str, str, int, str, str], dict[str, Any]] = {}
    damage_sources: dict[tuple[str, str, str, str, str], list[int]] = defaultdict(lambda: [0, 0])
    last_damage_by_target: dict[str, dict[str, Any]] = {}
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
        source_guid = fields[1] if len(fields) > 1 else ""
        source_name = fields[2] if len(fields) > 2 else ""
        target_guid = fields[5] if len(fields) > 5 else ""
        target_name = fields[6] if len(fields) > 6 else ""
        for actor_guid, actor_name in ((source_guid, source_name), (target_guid, target_name)):
            if actor_guid.startswith("Player-") and actor_name and actor_name != "nil":
                if current is not None:
                    current["roster"][actor_guid] = actor_name
        if event == "ENCOUNTER_START" and len(fields) >= 3:
            if current is not None:
                current["end"] = timestamp
                current["kill"] = None
                current["duration_seconds"] = round(max(0, timestamp - current["start"]) / 1000, 1)
                current["debuffs"] = _debuff_rows(aura_totals, current["start"], timestamp, current["name"], pending_auras, observed_stacks, aura_applications)
                current["armor_reduction"] = _armor_rows(current["debuffs"])
                current["long_buffs"] = _long_buff_coverage(long_buff_intervals, active_long_buffs, current, timestamp)
                current["damage_sources"] = _damage_source_rows(damage_sources)
                pending_auras.clear()
                aura_totals.clear()
                observed_stacks.clear()
                aura_applications.clear()
                damage_sources.clear()
                last_damage_by_target.clear()
            current = {"id": fields[1], "name": fields[2], "start": timestamp, "end": None, "kill": None, "roster": {}, "deaths": []}
            encounters.append(current)
            pending_auras.clear()
            aura_totals.clear()
            observed_stacks.clear()
            aura_applications.clear()
            damage_sources.clear()
            last_damage_by_target.clear()
        elif current is not None and event == "ENCOUNTER_END":
            current["end"] = timestamp
            current["kill"] = fields[5] == "1" if len(fields) > 5 else None
            current["debuffs"] = _debuff_rows(aura_totals, current["start"], timestamp, current["name"], pending_auras, observed_stacks, aura_applications)
            current["armor_reduction"] = _armor_rows(current["debuffs"])
            current["duration_seconds"] = max(1, (timestamp - current["start"]) / 1000)
            current["long_buffs"] = _long_buff_coverage(long_buff_intervals, active_long_buffs, current, timestamp)
            current["damage_sources"] = _damage_source_rows(damage_sources)
            current = None
            pending_auras.clear()
            aura_totals.clear()
            observed_stacks.clear()
            aura_applications.clear()
            damage_sources.clear()
            last_damage_by_target.clear()
        elif current is not None and event == "UNIT_DIED" and target_guid.startswith("Player-"):
            final_hit = last_damage_by_target.get(target_guid)
            if final_hit and timestamp - final_hit["timestamp"] > 2500:
                final_hit = None
            current["deaths"].append({
                "timestamp_seconds": round((timestamp - current["start"]) / 1000, 1),
                "player": target_name,
                "last_hit": {key: value for key, value in final_hit.items() if key != "timestamp"} if final_hit else None,
            })
        elif event.startswith("SPELL_AURA_") and len(fields) >= 13:
            source, target = source_guid, target_guid
            try:
                spell_id = int(fields[9])
            except ValueError:
                spell_id = 0
            spell, aura_type = fields[10], fields[12]
            if aura_type == "BUFF" and target.startswith("Player-") and _long_buff_family(spell):
                key = (target, target_name, spell_id, spell, source)
                if event in ("SPELL_AURA_APPLIED", "SPELL_AURA_REFRESH", "SPELL_AURA_APPLIED_DOSE"):
                    previous = active_long_buffs.pop(key, None)
                    if previous:
                        long_buff_intervals.append({**previous, "end": timestamp})
                    active_long_buffs[key] = {"target_id": target, "target": target_name, "spell_id": spell_id, "ability": spell,
                                              "family": _long_buff_family(spell), "provider": source_name, "start": timestamp}
                elif "REMOVED" in event or "BROKEN" in event:
                    previous = active_long_buffs.pop(key, None)
                    if previous:
                        long_buff_intervals.append({**previous, "end": timestamp})
                continue
            if aura_type != "DEBUFF":
                continue
            if current is None or target.startswith("Player-"):
                continue
            key = (target, target_name, spell_id, spell, source_name, source.startswith("Player-"), target_name.casefold() == current["name"].casefold())
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
                if event in ("SPELL_AURA_APPLIED", "SPELL_AURA_REFRESH", "SPELL_AURA_APPLIED_DOSE"):
                    aura_applications[key] += 1
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

        if current is not None and event in {"SWING_DAMAGE", "SPELL_DAMAGE", "SPELL_PERIODIC_DAMAGE", "RANGE_DAMAGE", "DAMAGE_SHIELD", "DAMAGE_SPLIT", "ENVIRONMENTAL_DAMAGE"} and target_guid.startswith("Player-"):
            hit = _damage_event(event, fields)
            if hit:
                ability, damage_type, amount = hit
                source = source_name if source_name and source_name != "nil" else "Environment"
                key = (target_guid, target_name, source, ability, damage_type)
                damage_sources[key][0] += amount
                damage_sources[key][1] += 1
                last_damage_by_target[target_guid] = {"timestamp": timestamp, "source": source, "ability": ability, "damage_type": damage_type, "amount": amount}

    if current is not None:
        current["end"] = last_timestamp
        current["kill"] = None
        current["duration_seconds"] = round(max(0, last_timestamp - current["start"]) / 1000, 1)
        current["debuffs"] = _debuff_rows(aura_totals, current["start"], last_timestamp, current["name"], pending_auras, observed_stacks, aura_applications)
        current["armor_reduction"] = _armor_rows(current["debuffs"])
        current["long_buffs"] = _long_buff_coverage(long_buff_intervals, active_long_buffs, current, last_timestamp)
        current["damage_sources"] = _damage_source_rows(damage_sources)
    for fight in encounters:
        if fight.get("end") and not fight.get("debuffs"):
            fight["debuffs"] = []
            fight["armor_reduction"] = []
        fight.pop("start", None)
        fight.pop("end", None)
        fight["roster"] = [{"id": guid, "name": name} for guid, name in sorted(fight.pop("roster", {}).items(), key=lambda item: item[1].casefold())]
    if not encounters:
        raise ValueError("No ENCOUNTER_START events found. Upload a WoW advanced combat log.")
    return {"file_name": None, "encounters": encounters, "encounter_count": len(encounters), "line_count": line_count}


def _damage_event(event: str, fields: list[str]) -> tuple[str, str, int] | None:
    if event == "ENVIRONMENTAL_DAMAGE":
        ability_index = 9
        amount_index, school_index = (29, 32) if len(fields) >= 30 else (10, 12)
    elif event == "SWING_DAMAGE":
        ability_index = -1
        amount_index, school_index = (28, 31) if len(fields) >= 29 else (9, 11)
    else:
        ability_index = 10
        amount_index, school_index = (31, 34) if len(fields) >= 32 else (12, 11)
    try:
        amount = max(0, int(float(fields[amount_index])))
    except (IndexError, ValueError):
        return None
    ability = fields[ability_index] if ability_index >= 0 and len(fields) > ability_index else "Melee"
    if event == "ENVIRONMENTAL_DAMAGE":
        ability = f"Environmental · {ability}"
    try:
        school = int(fields[school_index], 0)
    except (IndexError, ValueError):
        school = 0
    schools = [(mask, name) for mask, name in ((1, "Physical"), (2, "Holy"), (4, "Fire"), (8, "Nature"), (16, "Frost"), (32, "Shadow"), (64, "Arcane")) if school & mask]
    damage_type = "/".join(name for _, name in schools) or "Unknown type"
    return ability, damage_type, amount


def _damage_source_rows(totals: dict[tuple[str, str, str, str, str], list[int]]) -> list[dict[str, Any]]:
    by_player: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for (_, player, source, ability, damage_type), (amount, hits) in totals.items():
        by_player[(player, "")].append({"source": source, "ability": ability, "damage_type": damage_type, "amount": amount, "hits": hits})
    return [{"player": player, "sources": sorted(sources, key=lambda item: (-item["amount"], item["ability"]))[:8]}
            for (player, _), sources in sorted(by_player.items())]


def _debuff_rows(totals: dict, start: int, end: int, boss_name: str, pending: dict | None = None, observed_stacks: dict | None = None, applications: dict | None = None) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str, str, str, bool, bool], list[int]] = defaultdict(lambda: [0, 1])
    pending = pending or {}
    observed_stacks = observed_stacks or {}
    applications = applications or {}
    for key, elapsed in totals.items():
        target_id, target, spell_id, spell, provider, provider_is_player, target_is_boss = key
        active = pending.get(key)
        duration = elapsed + (max(0, end - active[0]) if active else 0)
        stacks = max(active[1] if active else 1, observed_stacks.get(key, 1))
        aggregate = grouped[(spell_id, spell, target, provider, provider_is_player, target_is_boss)]
        aggregate[0] += duration
        aggregate[1] = max(aggregate[1], stacks)
        if len(aggregate) < 3:
            aggregate.append(0)
        aggregate[2] += applications.get(key, 0)
    rows = []
    for (spell_id, spell, target, provider, provider_is_player, target_is_boss), (uptime_ms, stacks, application_count) in grouped.items():
        rows.append({"spell_id": spell_id, "ability": spell, "target": target, "provider": provider,
                     "provider_is_player": provider_is_player, "target_is_boss": target_is_boss,
                     "uptime_seconds": round(uptime_ms / 1000, 1), "uptime_percent": round(100 * uptime_ms / max(1, end - start), 1),
                     "fight_duration_seconds": round((end - start) / 1000, 1), "applications": application_count,
                     "armor_reduction": ARMOR_REDUCTION.get(spell, 0) or STACKING_ARMOR_REDUCTION.get(spell, 0) * stacks,
                     "armor_reduction_note": "estimated at the logged stack count" if spell in STACKING_ARMOR_REDUCTION else "estimated from the TBC spell rank"})
    return sorted(rows, key=lambda row: (-row["uptime_seconds"], row["ability"]))


def _long_buff_coverage(
    intervals: list[dict[str, Any]],
    active: dict[tuple[str, str, int, str, str], dict[str, Any]],
    fight: dict[str, Any],
    fight_end: int,
) -> list[dict[str, Any]]:
    fight_start = fight["start"]
    duration_ms = max(1, fight_end - fight_start)
    roster: dict[str, str] = fight.get("roster", {})
    coverage: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    all_intervals = [*intervals, *({**item, "end": fight_end} for item in active.values())]
    for aura in all_intervals:
        target_id = aura["target_id"]
        if target_id not in roster:
            continue
        overlap_start = max(fight_start, aura["start"])
        overlap_end = min(fight_end, aura["end"])
        if overlap_end <= overlap_start:
            continue
        row = coverage[aura["family"]].setdefault(
            target_id,
            {"id": target_id, "name": roster[target_id], "intervals": []},
        )
        row["intervals"].append((overlap_start, overlap_end, aura["start"] < fight_start))

    results = []
    for family, players_with_buff in sorted(coverage.items()):
        players = []
        for actor_id, actor_name in sorted(roster.items(), key=lambda item: item[1].casefold()):
            player = players_with_buff.get(actor_id)
            merged_intervals: list[list[int]] = []
            if player:
                for interval_start, interval_end, _ in sorted(player["intervals"]):
                    if merged_intervals and interval_start <= merged_intervals[-1][1]:
                        merged_intervals[-1][1] = max(merged_intervals[-1][1], interval_end)
                    else:
                        merged_intervals.append([interval_start, interval_end])
            uptime_ms = sum(interval_end - interval_start for interval_start, interval_end in merged_intervals)
            present_before_pull = bool(player and any(interval[2] for interval in player["intervals"]))
            players.append({
                "id": actor_id,
                "name": actor_name,
                "uptime_seconds": round(uptime_ms / 1000, 1),
                "uptime_percent": round(100 * uptime_ms / duration_ms, 1),
                "present_before_pull": present_before_pull,
                "status": "Not seen" if not player else "On at pull" if present_before_pull else "Applied in fight",
            })
        covered = sum(player["uptime_seconds"] > 0 for player in players)
        results.append({"ability": family, "covered_players": covered, "roster_size": len(players), "players": players})
    return results


def _armor_rows(debuffs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for row in debuffs:
        if not row["armor_reduction"]:
            continue
        item = totals.setdefault(row["ability"], {"ability": row["ability"], "estimated_armor_reduction": row["armor_reduction"], "uptime_seconds": 0.0, "targets": set()})
        item["estimated_armor_reduction"] = max(item["estimated_armor_reduction"], row["armor_reduction"])
        item["uptime_seconds"] += row["uptime_seconds"]
        item["targets"].add(row["target"])
    return [{**item, "uptime_seconds": round(item["uptime_seconds"], 1), "targets": len(item["targets"])} for item in totals.values()]
