"""game/gather.py: the units of an allied player (the same team of aoe2mc.json) are not enemies (#1312)."""
from test_gather import FakeServer, grid

from game import gather

UNITS = [{"kind": "unit", "name": "MILITIA", "player": p, "uuid": f"m-{p}", "tile": [2.5 + p, 2.5]} for p in (1, 2, 3)]


def enemies(teams):
    data = grid([[64] * 10 for _ in range(10)], UNITS)
    data["players"] = {str(p): {"civ": "BRITONS", "team": t} for p, t in teams.items()}
    return set(gather.Gather(FakeServer({}), data).enemies)


def test_an_ally_is_no_enemy():
    assert enemies({0: None, 1: 1, 2: 1, 3: 2}) == {"m-3"}


def test_without_teams_all_other_players_are_enemies():
    assert enemies({0: None, 1: None, 2: None, 3: None}) == {"m-2", "m-3"}
    assert enemies({}) == {"m-2", "m-3"}                               # a scenario: no players table


def test_allied():
    players = {"1": {"team": 1}, "2": {"team": 1}, "3": {"team": 2}, "4": {"team": None}}
    assert gather.allied(players, 1, 2) and gather.allied(players, 4, 4) and gather.allied(players, 1, 1)
    assert not gather.allied(players, 1, 3) and not gather.allied(players, 4, 1) and not gather.allied(players, 1, 4)
