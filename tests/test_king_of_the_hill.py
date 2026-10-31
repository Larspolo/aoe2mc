"""game/hill.py: the AoE2 victory "King of the Hill" (#2360, AoE2 wiki "King of the Hill", "Monument"). The units of a
player near the monument take it and start its timer of 550 years; an enemy unit takes it only when no unit of the
owner is there. At the end of the timer the owner and its allies win."""
import pytest
from test_gather import FakeServer, grid
from test_victory_option import loop

from game import gather, hill, wonder

YEAR = wonder.YEAR


def setup(*units, monument=True, teams=None):
    """A flat 32 × 32 map (tile size 1) with a MONUMENT at tile (16, 16) and the units (uuid, player, x, z); the units
    of player 1 are own soldiers, the others are units of aoe2mc.json."""
    objects = [{"kind": "building", "name": "MONUMENT", "player": 0, "tile": [16.0, 16.0],
                "footprint": [15, 15, 17, 17]}] * monument
    for uuid, player, x, z in units:
        objects.append({"kind": "unit", "name": "MILITIA", "player": player, "uuid": uuid, "tile": [x, z]})
    server = FakeServer({u: {"Pos": (x, 64.0, z)} for u, _, x, z in units})
    data = grid([[64] * 32 for _ in range(32)], objects)
    data["players"] = {str(p): {"team": t} for p, t in (teams or {}).items()}
    data["level_height"] = 1                                           # hill.place draws a monument without one
    g = gather.Gather(server, data).setup()
    for uuid, player, *_ in units:
        if player == 1:
            g.soldiers[uuid] = "MILITIA"
    return server, g


def run(g, seconds, step=1.0):
    for _ in range(round(seconds / step)):
        hill.tick(g, step)


def test_the_units_of_a_player_near_the_monument_start_its_timer_and_win():
    server, g = setup(("a", 1, 18.5, 16.5), ("e", 2, 30.5, 30.5))
    run(g, 10)
    assert g.hill["owner"] == 1 and g.hill["left"] == pytest.approx((hill.YEARS - 2) * YEAR, abs=YEAR)
    assert 'bossbar add aoe2mc:hill ""' in server.log and not g.ended
    run(g, hill.YEARS * YEAR)
    assert g.ended == "Victory" and 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log
    assert "bossbar remove aoe2mc:hill" in server.log


def test_no_unit_near_the_monument_starts_no_timer():
    server, g = setup(("a", 1, 2.5, 2.5), ("e", 2, 30.5, 30.5))
    run(g, 60)
    assert g.hill["owner"] is None and g.hill["left"] == hill.YEARS * YEAR
    assert not g.ended and not any(hill.BAR in c for c in server.log)


def test_an_enemy_unit_takes_the_monument_only_when_no_own_unit_is_there():
    server, g = setup(("a", 1, 18.5, 16.5), ("e", 2, 30.5, 30.5))
    run(g, 460 * YEAR)                                                 # less than 100 years left
    server.entities["e"]["Pos"] = (16.5, 64.0, 14.5)                  # nearer than the own unit: the owner stays
    run(g, 4)
    assert g.hill["owner"] == 1 and g.hill["left"] < 95 * YEAR
    server.entities["a"]["Pos"] = (2.5, 64.0, 2.5)                   # the own unit goes away: player 2 takes it
    run(g, 4)
    assert g.hill["owner"] == 2 and g.hill["left"] == pytest.approx(hill.RESET * YEAR, abs=4)   # back to 100 years
    assert any("Player 2 holds the monument." in c for c in server.log)
    run(g, hill.RESET * YEAR)
    assert g.ended == "Defeat"


def test_the_timer_goes_on_for_the_new_owner():
    server, g = setup(("a", 1, 18.5, 16.5), ("e", 2, 30.5, 30.5))
    run(g, 300 * YEAR)                                                 # 250 years left
    server.entities["a"]["Pos"], server.entities["e"]["Pos"] = (2.5, 64.0, 2.5), (16.5, 64.0, 14.5)
    run(g, 4)
    assert g.hill["owner"] == 2 and 240 * YEAR < g.hill["left"] < 250 * YEAR


def test_an_ally_wins_with_the_owner_and_the_map_center_without_a_monument():
    server, g = setup(("a", 2, 16.5, 16.5), monument=False, teams={1: 1, 2: 1})
    assert hill.center(g) == (16.0, 16.0)
    run(g, hill.YEARS * YEAR + 4)
    assert g.ended == "Victory" and 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log


def test_the_setting_runs_the_hill_and_not_the_wonder_or_relic_timer(monkeypatch):
    monkeypatch.setattr(gather.hill, "tick", lambda g, dt: None)
    calls = loop(monkeypatch, "king-of-the-hill")
    assert calls.count("conquest") == 4 and "wonder" not in calls and "relic_victory" not in calls
