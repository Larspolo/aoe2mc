"""The live minimap shows only what lives now (#1940): aoe2mc.json has the bare ground of map 0, the plugin paints it
under the dots, and the replay draws the start buildings as squares and removes a razed one. Fake RCON, a converted
world, and the plugin with a real client."""
import json
import os
import shutil
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402

import aoe2mc  # noqa: E402

HOUSE = {"id": 70, "ref": 5, "name": "HOUSE", "kind": "building", "player": 1, "x": 3.0, "y": 3.0,
         "footprint": [8, 8, 16, 16]}
BARRACKS = {"id": 12, "ref": 6, "name": "BARRACKS", "kind": "building", "player": 2, "x": 11.5, "y": 11.5,
            "footprint": [40, 40, 52, 52]}


def starts(**kw):
    d = data([{"time": 0, "player": 1, "kind": "chat", "text": "hi"}])
    d["objects"] = [dict(HOUSE), dict(BARRACKS)]
    return replay.Replay(Fake(), d, **kw)


def minimap(cmds):
    return [c for c in cmds if c.startswith("aoe minimap building") or c.startswith("aoe minimap unbuild")]


def test_the_replay_start_draws_each_start_building_once():
    r = starts(ai=True)
    r.run(clock=lambda: 0.0, sleep=lambda s: None, log=None, bar=True)
    assert minimap(r.game.sent) == ["aoe minimap building 8 8 16 16 p1", "aoe minimap building 40 40 52 52 p2"]
    r = starts()                                                       # vanilla: no plugin
    r.run(clock=lambda: 0.0, sleep=lambda s: None, log=None, bar=True)
    assert not minimap(r.game.sent)


def test_a_razed_start_building_leaves_the_minimap():
    r = starts(ai=True)
    r.run(clock=lambda: 0.0, sleep=lambda s: None, log=None, bar=True)
    assert minimap(r.commands(delete(500, [5]))) == ["aoe minimap unbuild 8 8"]
    assert not minimap(r.commands(delete(600, [5])))                   # once only


def test_a_razed_start_building_leaves_the_minimap_of_a_view_player():
    r = starts(ai=True, pov=1)
    assert minimap(r.minimap_buildings({1}, set())) == ["aoe minimap building 8 8 16 16 p1"]   # the enemy: not seen
    seen = {(x, z) for x in range(10, 13) for z in range(10, 13)}
    assert minimap(r.minimap_buildings({1}, seen)) == ["aoe minimap building 40 40 52 52 p2"]
    r.commands(delete(500, [5]))
    assert minimap(r.minimap_buildings({1}, seen)) == ["aoe minimap unbuild 8 8"]


def ground(world):
    with open(os.path.join(world, "aoe2mc.json")) as f:
        d = json.load(f)
    return d, np.array([list(bytes.fromhex(row)) for row in d["map_ground"]], np.uint8)


def test_aoe2mc_json_has_the_bare_ground_of_map_0(tiny_world):
    from PIL import Image
    d, bare = ground(tiny_world[0])
    colors, s, c = aoe2mc.map_colors(np.asarray(Image.open(os.path.join(tiny_world[0], "preview.png"))))
    assert bare.shape == (128, 128) and (bare == colors).all()
    archer = next(o for o in d["objects"] if o["name"] == "ARCHER")
    x, z = int(archer["tile"][0] * d["tile_size"]), int(archer["tile"][1] * d["tile_size"])
    px, pz = ((b - (c - (64 << s))) >> s for b in (x, z))
    drawn = aoe2mc.map_objects(colors.copy(), s, c, [{"kind": "U", "player": 2, "name": "ARCHER", "x": archer["tile"][0],
                                                      "y": archer["tile"][1]}], T=d["tile_size"])
    assert drawn[pz, px] != bare[pz, px]                               # map 0 has the player color there


@pytest.mark.mc
def test_a_dead_start_unit_leaves_the_ground_color_on_a_server(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    d, bare = ground(world)
    archer = next(o for o in d["objects"] if o["name"] == "ARCHER")
    x, z = int(archer["tile"][0] * d["tile_size"]), int(archer["tile"][1] * d["tile_size"])
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("item replace entity aoe2mc weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]")
        assert "Minimap: on, bare ground" in game.command("aoe minimap on")
        game.command(f"kill {archer['uuid']}")
        time.sleep(3)
        px, pz = map(int, game.command(f"aoe minimap pixel {x} {z}").split()[-2:])
        assert game.command(f"aoe minimap tile {x} {z}").split()[3] == str(bare[pz, px])
