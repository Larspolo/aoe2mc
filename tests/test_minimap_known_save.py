"""#3079: the game program keeps the buildings that the team of a player saw (fog.remember), and a new fog of the team on
the minimap (after a load, after the second "polo") gets them again with `aoe minimap know`, so their squares stay on
the dark tiles (Minimap.java)."""
import json
import shutil
import time

import pytest
from test_gather import FakeServer, grid

from game import fog, gather, replay, savegame

CASTLE = {"kind": "building", "name": "CASTLE", "player": 2, "footprint": [8, 8, 10, 10]}   # tiles (8, 8) to (9, 9)


def setup(objects=(CASTLE,)):
    """A flat 16 × 16 map (tile size 1) with an enemy castle; player 1 has no sight yet."""
    server = FakeServer({})
    g = gather.Gather(server, {**grid([[64] * 16 for _ in range(16)], objects), "map_size": 16}).setup()
    g.fog = {"hidden": set(), "at": None, "tiles": set()}
    return server, g


def saw(g):
    """A tile of the castle comes in sight, then goes out of it."""
    g.fog["tiles"] = {(9, 9)}
    fog.remember(g, g.fog)
    fog.minimap(g, g.fog)
    g.fog["tiles"] = set()
    fog.remember(g, g.fog)
    fog.minimap(g, g.fog)


def test_the_first_minimap_after_a_load_sends_the_buildings_that_the_team_saw():
    _, g = setup()
    saw(g)
    assert g.fog["known"] == {(8, 8)}
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    assert d["players"]["1"]["known"] == [[8, 8]]
    _, h = setup()
    savegame.load(h, d)
    out = fog.minimap(h, h.fog)
    assert out[:2] == ["aoe minimap fog 1 16 p1", "aoe minimap know p1 8,8"]
    assert "aoe minimap dim p1 9,9,9" in out                          # the tile of the castle is dark, not black
    assert not [c for c in fog.minimap(h, h.fog) if "know" in c]       # only a new fog gets them


def test_after_two_polo_the_new_fog_gets_the_buildings_that_the_team_saw():
    server, g = setup()
    saw(g)
    g.reveal = "normal"
    assert fog.toggle(g) == "all" and "aoe minimap fog off p1" in server.log
    assert fog.toggle(g) == "normal"
    assert fog.minimap(g, g.fog)[:2] == ["aoe minimap fog 1 16 p1", "aoe minimap know p1 8,8"]


def test_a_building_out_of_sight_and_a_fallen_building_are_not_known():
    _, g = setup()
    g.fog["tiles"] = {(7, 7), (10, 10)}                                # next to the castle, not on it
    fog.remember(g, g.fog)
    assert g.fog["known"] == set()
    saw(g)
    g.data["objects"] = []                                             # the castle fell
    fog.remember(g, g.fog)
    assert g.fog["known"] == set() and "known" not in savegame.dump(g)["players"]["1"]


def test_many_buildings_go_in_commands_below_the_rcon_limit():
    keys = [(x, z) for x in range(0, 4000, 4) for z in (0, 1000)]
    out = fog.know("p3", keys)
    assert len(out) > 1 and all(len(c) <= replay.RCON_MAX for c in out)
    assert [k for c in out for k in c.split()[4:]] == [f"{x},{z}" for x, z in keys]


@pytest.mark.mc
def test_the_plugin_shows_a_known_building_in_a_new_fog(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("item replace entity aoe2mc weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]")
        for c in ("team add p7", "team modify p7 color red", "team add p8", "team modify p8 color blue",
                  "team join p8 aoe2mc"):
            game.command(c)
        assert "Minimap: on" in game.command("aoe minimap on")
        assert "Minimap buildings: 1" in game.command("aoe minimap building 16 16 24 24 p7")   # tiles (4, 4) to (5, 5)
        assert "Minimap fog: 8 tiles" in game.command("aoe minimap fog 4 8 p8")   # a load: the team saw nothing yet
        assert "Minimap know: 1 buildings" in game.command("aoe minimap know p8 16,16")
        assert "Minimap dim: 1 tiles" in game.command("aoe minimap dim p8 4,4,4")
        time.sleep(3)
        dim = game.command("aoe minimap tile 18 18 p8").split()
        assert dim[2] == "explored" and int(dim[3]) == 28 * 4 + 3        # the square in the dark shade of red
        assert "Minimap fog: 8 tiles" in game.command("aoe minimap fog 4 8 p8")   # a new fog without know
        assert "Minimap dim: 1 tiles" in game.command("aoe minimap dim p8 4,4,4")
        time.sleep(3)
        assert int(game.command("aoe minimap tile 18 18 p8").split()[3]) != 28 * 4 + 3   # no square: not known
