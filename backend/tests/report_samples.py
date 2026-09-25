REPORT_START = 1_700_000_000_000


def fresh_report() -> dict:
    return {
        "code": "AbC123",
        "title": "Tuesday Raid",
        "startTime": REPORT_START,
        "endTime": REPORT_START + 3_600_000,
        "zone": {"name": "The Molten Core"},
        "guild": {"name": "Example Guild"},
        "fights": [
            {
                "id": 1,
                "encounterID": 100,
                "name": "Lucifron",
                "startTime": 10_000,
                "endTime": 70_000,
                "kill": False,
                "fightPercentage": 21.5,
                "friendlyPlayers": [11, 12],
            },
            {
                "id": 2,
                "encounterID": 100,
                "name": "Lucifron",
                "startTime": 90_000,
                "endTime": 150_000,
                "kill": True,
                "fightPercentage": 0,
                "friendlyPlayers": [11, 12],
            },
            {
                "id": 3,
                "encounterID": 0,
                "name": "Trash",
                "startTime": 160_000,
                "endTime": 175_000,
                "kill": None,
                "fightPercentage": None,
                "friendlyPlayers": [],
            },
        ],
    }
