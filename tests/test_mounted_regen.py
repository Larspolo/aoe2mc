"""A mounted unit does not heal (#850): the horse that holds its hit points (#732) regenerates in vanilla, the plugin
cancels that for a unit with AoE2 values."""
import shutil
import time

import pytest
from test_mounted_attack import floor
from test_ranged import data

from game import combat, run

CAVALIER = ('summon horse {x} {y} {z} {{NoAI:1b,Tame:1b,Tags:["k","k{i}"],'
            'equipment:{{saddle:{{id:"minecraft:saddle",count:1}}}},'
            'Passengers:[{{id:"minecraft:zombie",NoAI:1b,Tags:["kr"]}}]}}')


@pytest.mark.mc
def test_a_hurt_cavalier_does_not_heal(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0, n = 1, 200, 1, 10              # a horse heals 1 point with a chance of 1/900 per tick: 10 horses for 30 s
    with run.Game(world) as game:
        floor(game, x0, y, z0, 2 * n)
        for i in range(n):
            game.command(CAVALIER.format(x=x0 + 2 * i + 0.5, y=y, z=z0 + 2.5, i=i))
            game.command(combat.stats_command(f"@e[tag=k{i},limit=1]", "CAVALIER"))
            game.command(f"data modify entity @e[tag=k{i},limit=1] Health set value 100f")
        assert [data(game, f"k{i}", "Health") for i in range(n)] == [[100.0]] * n
        time.sleep(30)
        assert [data(game, f"k{i}", "Health") for i in range(n)] == [[100.0]] * n
