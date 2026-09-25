from app.services.report_normalizer import normalize_fight, normalize_report
from tests.report_samples import fresh_report


def test_normalize_report_and_boss_progression() -> None:
    report = normalize_report(fresh_report())
    assert report["code"] == "AbC123"
    assert report["title"] == "Tuesday Raid"
    assert report["zone"] == "The Molten Core"
    assert report["guild"] == "Example Guild"
    assert report["start_time"] == "2023-11-14T22:13:20Z"
    assert report["duration_ms"] == 3_600_000
    assert report["fight_count"] == 3
    assert report["boss_count"] == 1
    assert report["kill_count"] == 1
    assert report["wipe_count"] == 1
    assert report["bosses"][0]["attempts"] == 2
    assert report["bosses"][0]["name"] == "Lucifron"
    assert report["fights"][2]["kill"] is None


def test_normalize_fight_uses_relative_millisecond_offsets() -> None:
    fight = normalize_fight(fresh_report()["fights"][0])
    assert fight["fight_id"] == 1
    assert fight["encounter_id"] == 100
    assert fight["duration_ms"] == 60_000
    assert fight["friendly_players"] == [11, 12]
