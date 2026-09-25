from app.services.report_service import _friendly_damage_by_player


def test_friendly_damage_counts_player_sources_hitting_friendly_targets_only():
    events = {
        10: {
            "data": [
                {"targetID": 11, "amount": 125, "ability": {"guid": 1, "name": "Cleave"}},
                {"targetID": 99, "amount": 900, "ability": {"guid": 1, "name": "Cleave"}},
                {"targetID": 11, "amount": 25, "ability": {"guid": 1, "name": "Cleave"}},
            ],
            "nextPageTimestamp": None,
        },
        11: {"data": [], "nextPageTimestamp": None},
    }

    totals, abilities, complete = _friendly_damage_by_player(events, {10, 11})

    assert totals == {10: 150, 11: 0}
    assert abilities[10] == [{"id": 1, "name": "Cleave", "amount": 150, "hits": 2}]
    assert abilities[11] == []
    assert complete is True


def test_friendly_damage_marks_missing_or_paginated_data_incomplete():
    totals, _, complete = _friendly_damage_by_player(
        {10: {"data": [{"targetID": 11, "amount": 30}], "nextPageTimestamp": 5000}, 11: None},
        {10, 11},
    )

    assert totals == {10: 30}
    assert complete is False
