"""game/build.py and the Paper plugin (Gates.java): a gate opens for the own units and stays closed for the enemy
units (#1325, the decision #1323: option A)."""
import math
import shutil
import time
import types

import pytest
from test_build_gates import line
from test_build_site import site_map
from test_plugin import pos

from game import build, run


def test_a_complete_gate_gets_closed_doors_and_the_plugin_gate_on_paper():
    server, g = site_map(wood=200)
    g.paper = True
    line(g, (6, 10), (11, 10))
    site = build.gate(g, "Steve", "PALISADE_GATE", (8, 10))
    assert not any(c.startswith("aoe gate") for c in server.log)       # a foundation has no doors
    build.rise(g, site, math.inf)
    doors = [c for c in server.log if "_door[" in c]
    assert doors == [f"setblock {x} {y} 10 minecraft:spruce_door[facing=south,half={h},hinge={k}]"
                     for x, k in ((7, "left"), (8, "right")) for y, h in ((64, "lower"), (65, "upper"))]
    assert server.log[-1] == "aoe gate p1 7 64 10 8 65 10"


def test_a_gate_along_z_has_its_doors_along_z_and_a_redraw_puts_them_again():
    server, g = site_map(wood=200, chosen=0)
    g.stock["stone"] = 100
    line(g, (15, 6), (15, 11))
    site = build.gate(g, "Steve", "GATE", (15, 7))
    build.rise(g, site, math.inf)
    assert not any(c.startswith("aoe gate") for c in server.log)       # vanilla: the doors stay closed
    assert sum("dark_oak_door[facing=east" in c for c in server.log) == 4
    server.log.clear()
    g.techs, command = {"FEUDAL_AGE", "CASTLE_AGE", "FORTIFIED_WALL"}, g.command
    g.command = lambda c: "Gate has 1650 [aoe_hp]" if c.startswith("scoreboard players get") else command(c)
    build.upgrade(g, site, types.SimpleNamespace(hp=1650))             # the fortified design clears the passage
    assert [c.split()[1:4] for c in server.log if "_door[" in c][::2] == [["15", "64", "7"], ["15", "64", "8"]]


@pytest.mark.mc
def test_the_gate_opens_for_an_own_unit_and_not_for_an_enemy(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0, n = 1, 200, 1, 30                                       # a floor in the air, inside the world border
    gx, wz = x0 + 8, z0 + 12                                           # the gate: blocks gx .. gx + 3 of the wall wz
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + n + 2} {z0 + n + 2}")
        game.command(f"fill {x0} {y - 1} {z0} {x0 + n} {y - 1} {z0 + n} stone_bricks")
        game.command(f"fill {x0} {y} {wz} {x0 + n} {y + 3} {wz} stone")   # the wall from edge to edge
        game.command(f"fill {gx + 1} {y} {wz} {gx + 2} {y + 2} {wz} air")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        g = types.SimpleNamespace(command=game.command, paper=True, map=types.SimpleNamespace(T=1, y=lambda x, z: y))
        build.doors(g, {"name": "PALISADE_GATE", "player": 1, "footprint": (gx, gx + 4, wz, wz + 1)})

        def door(x):                                                   # True when the door at block x is open
            return "passed" in game.command(f"execute if block {x} {y} {wz} minecraft:spruce_door[open=true]")
        assert not door(gx + 1) and not door(gx + 2)
        units = {"own": (gx + 1.5, "p1"), "enemy": (x0 + 22.5, "p2")}  # both start 8 blocks north of the wall
        for tag, (x, team) in units.items():
            game.command(f'summon zombie {x} {y} {wz - 8 + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
        for tag, (x, _) in units.items():                              # each one to the south of the wall
            assert game.command(f"aoe moveto @e[tag={tag}] {x} {y} {wz + 8 + 0.5}").strip() == "Moved 1 units"
        end, opened = time.time() + 30, False
        while time.time() < end and not (pos(game, "own") and pos(game, "own")[2] > wz + 6):
            opened |= door(gx + 1)
            time.sleep(0.2)
        assert opened and pos(game, "own")[2] > wz + 6, pos(game, "own")       # through the open gate
        time.sleep(2)
        assert not door(gx + 1) and not door(gx + 2)                    # closed again: no own unit near
        assert pos(game, "enemy")[2] < wz, pos(game, "enemy")          # the enemy stays on its side
