"""The enemy buildings that a civilization sees under the fog of war (civs.REVEAL, fog.revealed, #2311): here the
Mapuche see the enemy castles at any distance, the Vietnamese the enemy start town centers at the start of the game
(own values of the test, in place of the key "reveal" of game/data/civs.jsonl)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import civs  # noqa: E402
import fog  # noqa: E402
import gather  # noqa: E402

T = 4
OWN, FOE = "00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000b1"
CASTLE = {"kind": "building", "name": "CASTLE", "player": 2, "footprint": [100 * T, 100 * T, 104 * T, 104 * T]}
TC = {"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": [80 * T, 20 * T, 84 * T, 24 * T]}


@pytest.fixture(autouse=True)
def reveal(monkeypatch):
    monkeypatch.setattr(civs, "REVEAL", {"MAPUCHE": [("CASTLE", False)], "VIETNAMESE": [("TOWN_CENTER", True)]})


def bare(civ, objects=(CASTLE, TC)):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper = 1, {"objects": list(objects), "players": {"1": {"civ": civ}}}, \
        types.SimpleNamespace(T=T), True
    g.villagers, g.soldiers, g.sites, g.enemies = {OWN: None}, {}, [], {FOE: "MILITIA"}
    g.players, g.bots, g.sent, g.now, g.reveal = {}, [], [], 0.0, "normal"
    g.command, g.clock = g.sent.append, lambda: g.now
    return g


def at(x, y):
    return (x + 0.5) * T, 70.0, (y + 0.5) * T


def hidden(g, foe):
    """True when the enemy unit at the tile foe hides for the player, with the own villager far away at (10, 10)."""
    return any(FOE in c for c in fog.update(g, {OWN: at(10, 10), FOE: at(*foe)}) if c.startswith("aoe hide"))


def test_the_mapuche_see_an_enemy_castle_at_any_distance():
    assert not hidden(bare("MAPUCHE"), (102, 102))
    assert hidden(bare("MAPUCHE"), (110, 110))                       # next to the castle: out of sight
    assert hidden(bare("BRITONS"), (102, 102))


def test_the_mapuche_see_a_castle_that_an_enemy_built_in_the_game():
    g = bare("MAPUCHE", objects=())
    foe = types.SimpleNamespace(player=2, sites=[{"name": "CASTLE", "footprint": (60 * T, 64 * T, 60 * T, 64 * T),
                                                  "progress": 1.0}])
    g.bots = [types.SimpleNamespace(g=foe)]
    assert fog.revealed(g) == {(x, z) for x in range(60, 64) for z in range(60, 64)}
    foe.sites[0]["progress"] = 0.5                                   # a foundation: not yet a castle
    assert fog.revealed(g) == set()


def test_the_mapuche_do_not_see_an_allied_castle_or_one_of_gaia():
    g = bare("MAPUCHE", objects=[{**CASTLE, "player": 3}, {**CASTLE, "player": 0}])
    g.players = {"1": {"team": 1}, "3": {"team": 1}}
    assert fog.revealed(g) == set()


def test_the_vietnamese_see_the_enemy_start_town_centers_only_at_the_start():
    g = bare("VIETNAMESE")
    assert fog.revealed(g, start=True) == {(x, z) for x in range(80, 84) for z in range(20, 24)}
    assert not hidden(g, (82, 22))                                   # the first update: the start of the game
    assert hidden(g, (82, 22))
    assert hidden(bare("BRITONS"), (82, 22))
    assert hidden(bare("VIETNAMESE"), (102, 102))                    # no castle for the Vietnamese
