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
            "uptime_seconds": 10.0,
            "uptime_percent": 33.3,
            "armor_reduction": 3075,
            "armor_reduction_note": "estimated from the TBC spell rank",
        }
    ]
    assert encounter["armor_reduction"][0]["estimated_armor_reduction"] == 3075


def test_decompress_combat_log_rejects_invalid_gzip() -> None:
    try:
        decompress_combat_log(b"not gzip")
    except ValueError as exc:
        assert "invalid or incomplete" in str(exc)
    else:
        raise AssertionError("Expected invalid gzip data to be rejected")
