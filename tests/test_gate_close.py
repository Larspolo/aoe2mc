"""The Paper plugin (Gates.java, AoePlugin.follow): the gate closes when an own villager has gone through it and stands
still (#1928). At the goal the plugin stops the AI of a villager; its old path through the gate kept the gate open,
and an enemy walked in."""
import shutil
import time
import types

import pytest
from test_plugin import pos

from game import build, run


@pytest.mark.mc
def test_the_gate_closes_after_an_own_villager_went_through(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0, n = 1, 200, 1, 30                                       # a floor in the air, as in test_gate_open.py
    gx, wz = x0 + 8, z0 + 12
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + n + 2} {z0 + n + 2}")
        game.command(f"fill {x0} {y - 1} {z0} {x0 + n} {y - 1} {z0 + n} stone_bricks")
        game.command(f"fill {x0} {y} {wz} {x0 + n} {y + 3} {wz} stone")
        game.command(f"fill {gx + 1} {y} {wz} {gx + 2} {y + 2} {wz} air")
        game.command("team add p1")
        g = types.SimpleNamespace(command=game.command, paper=True, map=types.SimpleNamespace(T=1, y=lambda x, z: y))
        build.portcullis(g, {"name": "PALISADE_GATE", "player": 1, "footprint": (gx, gx + 4, wz, wz + 1)})

        def down():                                                    # True when the bars are down (closed)
            return all("passed" in game.command(f"execute if block {gx + d} {y} {wz} minecraft:iron_bars") for d in (1, 2))
        assert down()
        game.command(f'summon villager {gx + 1.5} {y} {wz - 8 + 0.5} {{Tags:["own"]}}')
        game.command("team join p1 @e[tag=own]")
        assert game.command(f"aoe moveto @e[tag=own] {gx + 1} {y} {wz + 8}").strip() == "Moved 1 units"   # a block corner, as Gather
        end = time.time() + 30
        while time.time() < end and not (pos(game, "own") and pos(game, "own")[2] > wz + 6):
            time.sleep(0.2)
        assert pos(game, "own")[2] > wz + 6, pos(game, "own")             # through the gate, at its goal
        end = time.time() + 3
        while time.time() < end and not down():
            time.sleep(0.2)
        assert down(), pos(game, "own")                                 # no own unit near: the bars are down again
