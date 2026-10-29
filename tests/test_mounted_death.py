"""A mounted unit has one hit point pool (#732): a hit on the rider takes the health of the horse, and the rider dies
with the horse."""
import shutil
import time

import pytest

from game import combat, run
from test_mounted_attack import KNIGHT, floor, hits
from test_ranged import data


@pytest.mark.mc
def test_rider_dies_with_its_horse(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        game.command("difficulty hard")
        game.command(KNIGHT.format(x=x0 + 12.5, y=y, z=z0 + 2.5))
        game.command(f'summon skeleton {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=k]")
        game.command(combat.stats_command("@e[tag=k,limit=1]", "KNIGHT"))
        game.command(combat.range_command("@e[tag=a,limit=1]", "ARCHER", 4))
        game.command("aoe stats @e[tag=a,limit=1] 30 50 0 0 1 archer -")    # 50 - the pierce armor per arrow
        assert game.command("aoe attack @e[tag=a] @e[tag=kr,limit=1]").strip() == "Attack: 1 units"   # at the rider
        k = combat.stats("KNIGHT")
        per = 50 - k.pierce
        assert hits(game, "k", float(k.hp), 2, 30) == [k.hp - per, k.hp - 2 * per]   # the horse takes the hits on the rider
        assert data(game, "kr", "Health") == [20.0]                   # the rider keeps its own health
        end = time.time() + 15
        while time.time() < end and (data(game, "k", "Health") or data(game, "kr", "Health")):
            time.sleep(0.1)
        assert data(game, "k", "Health") is None, "the horse is alive"
        assert data(game, "kr", "Health") is None, "the rider is alive"
