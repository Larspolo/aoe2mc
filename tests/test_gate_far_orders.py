"""#3075: the orders of own units far from a gate do not open it: the enemy cannot walk in while the own villagers
work elsewhere (Gates.java, AoE2: the gate opens for the own units that pass)."""
import shutil
import time
import types

import pytest
from test_plugin import pos

from game import build, run


@pytest.mark.mc
def test_far_own_orders_keep_the_gate_closed_for_an_enemy(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0, n = 1, 200, 1, 40                                       # a floor in the air, inside the world border
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
        build.portcullis(g, {"name": "PALISADE_GATE", "player": 1, "footprint": (gx, gx + 4, wz, wz + 1)})
        own, enemy = (x0 + 32.5, wz + 20.5), (gx + 2.5, wz - 4 + 0.5)  # own: 20 blocks south, enemy: 4 north
        for tag, (x, z), team in (("own", own, "p1"), ("enemy", enemy, "p2")):
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
        game.command(f"aoe moveto @e[tag=enemy] {gx + 2.5} {y} {wz + 8 + 0.5}")
        end, opened, k = time.time() + 20, False, 0
        while time.time() < end:                                       # the legs of a villager at work
            x = own[0] + (3 if k % 2 else 0)
            game.command(f"aoe moveto @e[tag=own] {x} {y} {own[1]}")
            if k % 4 == 0:                                             # the enemy plans its way again
                game.command(f"aoe moveto @e[tag=enemy] {gx + 2.5} {y} {wz + 8 + 0.5}")
            opened |= all("passed" in game.command(f"execute if block {gx + 1} {y + d} {wz} minecraft:air")
                          for d in range(3))
            k += 1
            time.sleep(0.5)
        assert pos(game, "enemy")[2] < wz, pos(game, "enemy")          # the enemy stays north of the wall
        assert not opened                                              # the bars stay down
