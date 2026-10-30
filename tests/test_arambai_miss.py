"""The Arambai misses most of its darts, and a missed dart hurts an enemy unit near the target with its full damage
(#4549, AoE2 wiki "Arambai": accuracy 20 %, 30 % Elite, "Missed projectiles deal 100% damage too"): the keys
"accuracy" and "miss", combat.accuracy_command and `aoe accuracy` of the plugin. Test data, and arrows on a server."""
import re
import shutil
import time

import pytest

from game import combat, run
from test_unit_shield_wagon import health


def test_the_miss_key_adds_the_part_and_the_blocks(monkeypatch):
    monkeypatch.setattr(combat, "ACCURACY", {"TEST_DART": 0.2, "TEST_ROCK": 0.5})
    monkeypatch.setattr(combat, "MISS", {"TEST_DART": {"part": 1.0, "radius": 0.5}})
    assert combat.accuracy_command("u", "TEST_DART", 0.0, 4) == "aoe accuracy u 0.2 1 2"
    assert combat.accuracy_command("u", "TEST_ROCK", 0.0, 4) == "aoe accuracy u 0.5"
    assert combat.accuracy_command("u", "TEST_DART", 0.9, 4) is None      # 100 %: no command


@pytest.mark.mc
def test_a_missed_arrow_hurts_the_enemy_next_to_the_target_not_the_target(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    with run.Game(world) as game:
        game.command("forceload add 0 0 16 16")
        game.command(f"fill 0 {y - 1} 0 15 {y - 1} 15 stone_bricks")
        game.command("time set midnight")                 # a zombie burns in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton 14.5 {y} 14.5 {{NoAI:1b,Tags:["a"]}}')
        for tag, x, z, team in (("t", 2.5, 2.5, "p2"), ("n", 3.5, 2.5, "p2"), ("o", 2.5, 3.5, "p1")):
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 0 0 0 0 infantry -")
        game.command("team join p1 @e[tag=a]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER"))
        assert game.command("aoe accuracy @e[tag=a,limit=1] 0 1 2").strip() == "Accuracy: 1 units"
        out = game.command("data get entity @e[tag=a,limit=1] UUID")
        owner = ",".join(re.findall(r"-?\d+", out.split(":", 1)[-1]))
        game.command(f"summon arrow 2.5 {y + 2.5} 2.5 {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
        time.sleep(1.0)
        assert health(game, "t") == 1000                  # each shot misses the target
        assert health(game, "n") < 1000                   # the other enemy takes the dart
        assert health(game, "o") == 1000                  # not the own unit
