"""Live replay: the live units as dots on the map item (#1237, Minimap.java of the plugin). The place rule, the start
command of the replay (fake RCON) and the command on a real Paper server."""
import os
import re
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_deaths import start  # noqa: E402

import aoe2mc  # noqa: E402

# block (x or z) -> map pixel of a 480 x 480 world: scale 2 (4 blocks per pixel), pixel 0 starts at block -16
PLACES = {0: 4, 3: 4, 4: 5, 240: 64, 479: 123}


def test_the_place_rule_of_a_480_world_matches_the_map_of_the_converter():
    colors, s, c = aoe2mc.map_colors(np.zeros((480, 480, 3), np.uint8))
    assert (s, c) == (2, 240)
    for b, px in PLACES.items():                          # a unit at (b, b) colors pixel (px, px) of map_objects
        drawn = aoe2mc.map_objects(np.zeros((128, 128), np.uint8), s, c,
                                   [{"kind": "U", "player": 1, "name": "MILITIA", "x": b / 4, "y": b / 4}])
        assert list(zip(*np.nonzero(drawn))) == [(px, px)]


def test_the_replay_turns_the_minimap_on_on_paper():
    sent = start(ai=True)
    assert sent.count("aoe minimap on") == 1
    assert "aoe minimap on" not in start(ai=False)                     # vanilla has no plugin


@pytest.mark.mc
def test_the_minimap_command_on_a_server(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = str(tmp_path / "W")
    aoe2mc.convert(aoe2mc.RANDOM_MAP + "arabia", world)               # 480 x 480 blocks, units of players 1 and 2
    with run.Game(world) as game:
        game.forceload()
        for b, px in PLACES.items():
            assert f"Minimap pixel: {px} {px}" in game.command(f"aoe minimap pixel {b} {b}")
        assert "outside" in game.command("aoe minimap pixel -17 240")
        game.command("team add aoe_t1")
        game.command("team modify aoe_t1 color red")
        game.command("team add aoe_t2")
        game.command("team modify aoe_t2 color blue")
        for i, team in ((171, "aoe_t1"), (172, "aoe_t2")):
            game.command(f"summon minecraft:pillager {i} 80 200 {{UUID:[I;0,0,0,{i}],NoAI:1b}}")
            game.command(f"team join {team} 00000000-0000-0000-0000-0000000000{i:02x}")
        assert "Minimap: on" in game.command("aoe minimap on")
        game.command("give @a minecraft:filled_map[minecraft:map_id=0]")
        game.command("tick sprint 40")                                 # the renderer runs on the server ticks
        assert "Minimap: off" in game.command("aoe minimap off")
        assert "Minimap: on" in game.command("aoe minimap on")
        assert not re.search(r"(?i)exception|error", game.command("aoe minimap off"))
