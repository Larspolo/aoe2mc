"""The damage stages of a gate do not change its portcullis (#3073): wear() (AoePlugin.java) skips the box of a gate of
Gates.java and the row above it, so an open gate stays open for the own units at each stage, and the gate stands."""
import shutil
import time
import types

import pytest

from game import build, combat, run


@pytest.mark.mc
def test_the_bars_of_a_damaged_gate_stay_as_the_gate_sets_them(tiny_world, tmp_path):
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
        uuid, hp = combat.target_uuid([gx, wz, 4, 1]), combat.stats("PALISADE_GATE").hp
        for c in combat.building(uuid, "PALISADE_GATE", 1, (gx, y - 1, wz, gx + 3, y + 3, wz)):
            game.command(c)

        def state(block):                                              # True when all bars are this block
            return all("passed" in game.command(f"execute if block {gx + d} {y + h} {wz} minecraft:{block}")
                       for d in (1, 2) for h in range(3))

        def wait(block, seconds=5):
            end = time.time() + seconds
            while time.time() < end and not state(block):
                time.sleep(0.2)
            return state(block)
        assert state("iron_bars")
        game.command(f"scoreboard players set {uuid} aoe_hp {hp * 6 // 7 - 10}")   # stage 1 while closed
        time.sleep(2.5)
        assert state("iron_bars")
        game.command(f'summon villager {gx + 1.5} {y} {wz - 1 + 0.5} {{NoAI:1b,Tags:["own"]}}')
        game.command("team join p1 @e[tag=own]")
        assert wait("air")                                             # the own unit raises the bars
        game.command(f"scoreboard players set {uuid} aoe_hp {hp * 3 // 7 - 10}")   # stage 4 while open
        time.sleep(2.5)
        assert state("air")                                            # the bars stay raised
        game.command(f"scoreboard players set {uuid} aoe_hp 1")       # the last stage
        time.sleep(2.5)
        assert state("air")
        game.command("tp @e[tag=own] ~ ~ ~-10")
        assert wait("iron_bars")                                       # the unit leaves: the bars go down
        game.command(f"tp @e[tag=own] {gx + 1.5} {y} {wz - 1 + 0.5}")
        assert wait("air")                                             # the gate stands and opens again
