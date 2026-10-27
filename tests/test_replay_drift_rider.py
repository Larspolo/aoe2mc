"""`aoe where` (#1334): a mounted unit that the plugin sends at an enemy in its sight (the AoE2 default stance, #775)
has target 1 in each sample of its move. The rider has the target, not the horse, and Mob#setTarget of a plugin fires no
EntityTargetEvent: tools/replay_drift.py counted the scout cavalry of de-64.3 as "stray"."""
import math
import re
import shutil
import time

import pytest

from game import combat, run


@pytest.mark.mc
def test_a_rider_that_attacks_an_enemy_in_sight_is_a_fight_in_each_sample(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 20}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 36} {y - 1} {z0 + 16} stone_bricks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon horse {x0 + 2.5} {y} {z0 + 8.5} {{NoAI:1b,Tame:1b,Tags:["a"],'
                     'equipment:{saddle:{id:"minecraft:saddle",count:1}},'
                     'Passengers:[{id:"minecraft:zombie",NoAI:1b,Tags:["ar"]}]}')
        game.command(f'summon zombie {x0 + 18.5} {y} {z0 + 8.5} {{NoAI:1b,IsBaby:0b,Tags:["b"]}}')   # 4 tiles away
        game.command("team join p1 @e[tag=a]")
        game.command("team join p1 @e[tag=ar]")
        game.command("team join p2 @e[tag=b]")
        for tag, name in (("a", "SCOUT_CAVALRY"), ("b", "MILITIA")):
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        game.command("aoe where @e[tag=a]")                                   # clear the fights of the summon
        assert game.command(combat.sight_command("@e[tag=a,limit=1]", "SCOUT_CAVALRY", 4)).strip() == "Sight: 1 units"
        last, moves, end = None, [], time.time() + 20
        while time.time() < end and len(moves) < 3:
            m = re.search(r"Where 1: \S+ (\S+) \S+ (\S+) (\d) (\d)", game.command("aoe where @e[tag=a]"))
            assert m, "no answer of aoe where"
            x, z, target = float(m[1]), float(m[2]), m[4] == "1"
            if last and math.dist(last, (x, z)) > 0.5:
                moves.append(target)                                          # a sample after a move
            last = (x, z)
            time.sleep(0.5)
        assert moves and all(moves), moves                                    # it moved, and each move is a fight
