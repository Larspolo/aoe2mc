"""#2391: the start scout of a civilization (AoE2 wiki "Scout unit"): the Scout Cavalry of the map becomes the scout of
the civilization (scout.SCOUTS, for example an Eagle Scout for the Aztecs)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import run  # noqa: E402
import scout  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402


def game(civ):
    """Player 1 of civilization civ with a Scout Cavalry and a militia, player 2 with a Scout Cavalry."""
    objects = [{"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "uuid": "s-1", "tile": [3.5, 3.5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m-1", "tile": [5.5, 3.5]},
               {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 2, "uuid": "s-2", "tile": [15.5, 15.5]}]
    feet = {"s-1": (3.5, 64.0, 3.5), "m-1": (5.5, 64.0, 3.5), "s-2": (15.5, 64.0, 15.5)}
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    data = grid([[64] * 20 for _ in range(20)], objects)
    data["players"] = {"1": {"civ": civ}, "2": {"civ": "FRANKS"}}
    return server, gather.Gather(server, data).setup()


@pytest.mark.parametrize("civ", sorted(scout.SCOUTS))
def test_the_scout_cavalry_becomes_the_scout_of_the_civilization(civ):
    name = scout.SCOUTS[civ]                                           # the key "scout" of game/data/civs.jsonl
    server, g = game(civ)
    server.log.clear()
    scout.swap(g)
    assert "kill s-1" in server.log and "execute as s-1 on passengers run kill @s" in server.log
    new = [u for u, n in g.soldiers.items() if n == name]
    assert len(new) == 1 and "s-1" not in g.soldiers and g.soldiers["m-1"] == "MILITIA"
    summon, = [c for c in server.log if c.startswith("summon ")]
    assert summon.split()[2:5] == ["3.5", "64.0", "3.5"]               # at the place of the Scout Cavalry
    assert not any("s-2" in c for c in server.log)                     # not the scout of another player


def test_only_a_civilization_with_its_own_scout_needs_the_swap():
    assert scout.used({"players": {"1": {"civ": "FRANKS"}, "2": {"civ": "TUPI"}}})
    assert not scout.used({"players": {"1": {"civ": "FRANKS"}, "2": {}}}) and not scout.used({"players": []})


@pytest.mark.parametrize("civ", ["FRANKS", "BRITONS", None])
def test_the_other_civilizations_keep_the_scout_cavalry(civ):
    server, g = game(civ)
    server.log.clear()
    scout.swap(g)
    assert g.soldiers["s-1"] == "SCOUT_CAVALRY" and not server.log


@pytest.mark.parametrize("state, swaps", [(None, 1), ({"players": {}}, 0)])
def test_play_swaps_the_scouts_of_a_new_game_only(state, swaps, tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {"civ": "AZTECS"}}, "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(scout, "swap", seen.append)
    import combat
    import savegame
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(savegame, "load", lambda g, d: None, raising=False)
    from test_play_speed import FakeGame
    run.play(FakeGame(), str(tmp_path), state=state)
    assert len(seen) == swaps
