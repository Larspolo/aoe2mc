"""The Shrivamsha Rider dodges projectiles (#4399, AoE2 DE wiki "Shrivamsha Rider": "Can dodge five (seven for Elite)
consecutive projectiles in a 20 second time frame"): the key "dodge", game/abilities/dodge.py and `aoe dodge` of the
plugin. Test data, and arrows on a server."""
import re
import shutil
import time

import pytest
from abilities import dodge

from game import combat, run


def test_the_dodge_command_gives_the_shots_and_the_time_in_ticks(monkeypatch):
    monkeypatch.setattr(dodge, "UNITS", {"TEST_RIDER": {"shots": 3, "time": 12.5}})
    assert dodge.command("u-1", "TEST_RIDER") == "aoe dodge u-1 3 250"
    assert dodge.command("u-1", "ARCHER") is None


def data(game, tag, path):
    out = game.command(f"data get entity @e[tag={tag},limit=1] {path}")
    return [float(v) for v in re.findall(r"-?\d+\.?\d*(?=[df]?\b)", out.split(":", 1)[-1])]


@pytest.mark.mc
def test_the_first_arrows_do_no_damage_and_the_next_one_does(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x, y, z, shots = 4.5, 200, 4.5, 3
    with run.Game(world) as game:
        game.command("forceload add 0 0 16 16")
        game.command(f"fill 0 {y - 1} 0 15 {y - 1} 15 stone_bricks")
        game.command("time set midnight")                 # a zombie burns in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton 12.5 {y} 12.5 {{NoAI:1b,Tags:["a"]}}')
        game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER"))
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 cavalry -")
        assert game.command(f"aoe dodge @e[tag=t,limit=1] {shots} 100000").strip() == "Dodge: 1 units"   # no refill
        owner = ",".join(str(int(v)) for v in data(game, "a", "UUID"))
        hp = []
        for _ in range(shots + 1):                         # an arrow of the archer falls on the target
            game.command(f"summon arrow {x} {y + 2.5} {z} {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
            time.sleep(1.0)
            hp.append(data(game, "t", "Health")[0])
        assert hp[:shots] == [1000.0] * shots and hp[shots] < 1000, hp
