import gzip

from app.services.combat_log import analyze_combat_log, decompress_combat_log


def test_analyze_compressed_combat_log_tracks_debuff_provider_uptime_and_armor() -> None:
    source = 'Player-1,"Rogue",0x511,0x0'
    target = 'Creature-1,"Archimonde",0xa48,0x0'
    content = "\n".join(
        [
            "9/24/2026 20:00:00.0000  ENCOUNTER_START,622,\"Archimonde\",4,25",
            f"9/24/2026 20:00:10.0000  SPELL_AURA_APPLIED,{source},{target},26866,\"Expose Armor\",0x1,DEBUFF",
            f"9/24/2026 20:00:20.0000  SPELL_AURA_REMOVED,{source},{target},26866,\"Expose Armor\",0x1,DEBUFF",
            "9/24/2026 20:00:30.0000  ENCOUNTER_END,622,\"Archimonde\",4,25,1",
        ]
    ).encode()

    payload = analyze_combat_log(decompress_combat_log(gzip.compress(content)))

    assert payload["encounter_count"] == 1
    encounter = payload["encounters"][0]
    assert encounter["name"] == "Archimonde"
    assert encounter["kill"] is True
    assert encounter["debuffs"] == [
        {
            "spell_id": 26866,
            "ability": "Expose Armor",
            "target": "Archimonde",
            "provider": "Rogue",
            "provider_is_player": True,
            "target_is_boss": True,
            "uptime_seconds": 10.0,
            "uptime_percent": 33.3,
            "fight_duration_seconds": 30.0,
            "applications": 1,
            "armor_reduction": 3075,
            "armor_reduction_note": "estimated from the TBC spell rank",
        }
    ]
    assert encounter["armor_reduction"][0]["estimated_armor_reduction"] == 3075


def test_analyze_combat_log_classifies_non_player_boss_debuff_and_death_damage() -> None:
    npc = 'Creature-9,"Shadow Fiend",0xa48,0x0'
    player = 'Player-Dead,"Healer",0x514,0x0'
    boss = 'Creature-Boss,"Archimonde",0xa48,0x0'
    content = "\n".join(
        [
            "9/24/2026 20:00:00.0000  ENCOUNTER_START,622,\"Archimonde\",4,25",
            f"9/24/2026 20:00:01.0000  SPELL_AURA_APPLIED,{npc},{boss},123,\"Curse of Weakness\",0x20,DEBUFF",
            f"9/24/2026 20:00:04.0000  SPELL_DAMAGE,{npc},{player},123,\"Shadow Bolt\",0x20,350,0,0,0,0,0,false,false,false,false",
            f"9/24/2026 20:00:04.1000  UNIT_DIED,{npc},{player}",
            "9/24/2026 20:00:10.0000  ENCOUNTER_END,622,\"Archimonde\",4,25,0",
        ]
    ).encode()

    encounter = analyze_combat_log(content)["encounters"][0]

    assert encounter["debuffs"][0]["provider_is_player"] is False
    assert encounter["debuffs"][0]["target_is_boss"] is True
    assert encounter["deaths"][0]["last_hit"] == {
        "source": "Shadow Fiend",
        "ability": "Shadow Bolt",
        "damage_type": "Shadow",
        "amount": 350,
    }
    assert encounter["damage_sources"][0]["sources"][0]["amount"] == 350


def test_analyze_combat_log_closes_attempt_when_next_encounter_starts() -> None:
    npc = 'Creature-9,"Shadow Fiend",0xa48,0x0'
    player = 'Player-Dead,"Healer",0x514,0x0'
    content = "\n".join(
        [
            "9/24/2026 20:00:00.0000  ENCOUNTER_START,622,\"Archimonde\",4,25",
            f"9/24/2026 20:00:03.0000  SPELL_DAMAGE,{npc},{player},123,\"Shadow Bolt\",0x20,350,0,0,0,0,0,false,false,false,false",
            "9/24/2026 20:00:05.0000  ENCOUNTER_START,622,\"Archimonde\",4,25",
            "9/24/2026 20:00:10.0000  ENCOUNTER_END,622,\"Archimonde\",4,25,1",
        ]
    ).encode()

    first, second = analyze_combat_log(content)["encounters"]

    assert first["duration_seconds"] == 5.0
    assert first["damage_sources"][0]["sources"][0]["amount"] == 350
    assert second["duration_seconds"] == 5.0


def test_long_buff_coverage_uses_pull_state_and_full_fight_duration() -> None:
    mage = 'Player-Mage,"Mage",0x514,0x0'
    rogue = 'Player-Rogue,"Rogue",0x511,0x0'
    other = 'Player-Other,"Other",0x514,0x0'
    boss = 'Creature-Boss,"Archimonde",0xa48,0x0'
    content = "\n".join(
        [
            f"9/24/2026 19:59:50.0000  SPELL_AURA_APPLIED,{mage},{rogue},1459,\"Arcane Intellect\",0x40,BUFF",
            f"9/24/2026 19:59:55.0000  SWING_DAMAGE,{other},{boss},1,1,0,0,0,0,0,0,0,0,0,0,0",
            "9/24/2026 20:00:00.0000  ENCOUNTER_START,622,\"Archimonde\",4,25",
            f"9/24/2026 20:00:04.0000  SWING_DAMAGE,{mage},{boss},1,1,0,0,0,0,0,0,0,0,0,0,0",
            f"9/24/2026 20:00:05.0000  SWING_DAMAGE,{rogue},{boss},1,1,0,0,0,0,0,0,0,0,0,0,0",
            "9/24/2026 20:00:10.0000  ENCOUNTER_END,622,\"Archimonde\",4,25,1",
        ]
    ).encode()

    encounter = analyze_combat_log(content)["encounters"][0]
    buff = encounter["long_buffs"][0]
    assert buff["ability"] == "Arcane Intellect"
    assert buff["covered_players"] == 1
    assert [(player["name"], player["uptime_percent"], player["status"]) for player in buff["players"]] == [
        ("Mage", 0.0, "Not seen"),
        ("Rogue", 100.0, "On at pull"),
    ]


def test_decompress_combat_log_rejects_invalid_gzip() -> None:
    try:
        decompress_combat_log(b"not gzip")
    except ValueError as exc:
        assert "invalid or incomplete" in str(exc)
    else:
        raise AssertionError("Expected invalid gzip data to be rejected")
