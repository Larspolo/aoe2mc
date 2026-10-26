"""A ranged unit hits a standing target at about the AoE2 rate of fire (#634): the plugin aims its arrows."""
import shutil
import time

import pytest
from test_ranged import data

from game import combat, run


@pytest.mark.mc
def test_longbowman_hits_8_of_10_shots_at_19_blocks(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 24} {z0 + 8}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 22} {y - 1} {z0 + 6} stone_bricks")
        game.command("time set midnight")
        game.command("difficulty normal")     # the vanilla bow shot misses most arrows at 20 blocks on normal
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command(f'summon zombie {x0 + 19.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        cmd = combat.range_command("@e[tag=a,limit=1]", "LONGBOWMAN", 4)
        reload = int(cmd.split()[-1]) / 20                                 # 24 ticks: 1.2 s at Normal speed
        assert game.command(cmd).strip() == "Range: 1 units"
        game.command(combat.stats_command("@e[tag=a,limit=1]", "LONGBOWMAN"))
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 infantry -")    # many hit points, 6 per arrow
        assert game.command("aoe attack @e[tag=a] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        hits, last, start = [], 1000.0, time.time()
        while time.time() < start + 10 * reload:                       # 10 shots: the first one at once
            h = (data(game, "t", "Health") or [last])[0]
            if h < last:
                hits.append(time.time())
                last = h
            time.sleep(0.05)
        assert len(hits) >= 8, [round(t - start, 2) for t in hits]
        gaps = sorted(b - a for a, b in zip(hits, hits[1:]))
        assert gaps[len(gaps) // 2] <= 1.5 * reload, gaps
