"""The Iron Pagoda ignores one melee hit every 40 seconds (#4465, AoE2 DE wiki "Iron Pagoda": "Ignores one melee
attack every 40 (30 for Elite) seconds"): the field "melee" of the key "dodge", combat.dodge_command and the last
argument of `aoe dodge`. Test data, and a melee hit and an arrow on a server."""
import re
import shutil
import time

import pytest

from game import combat, run


def test_a_melee_dodge_adds_the_last_field_1(monkeypatch):
    monkeypatch.setattr(combat, "DODGE", {"KNIGHT": {"shots": 1, "time": 40, "melee": True},
                                          "TEST_RIDER": {"shots": 3, "time": 12.5}})
    assert combat.dodge_command("u-1", "KNIGHT") == "aoe dodge u-1 1 800 1"
    assert combat.dodge_command("u-1", "TEST_RIDER") == "aoe dodge u-1 3 250"


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    return float(re.findall(r"-?\d+\.?\d*", out.split(":", 1)[-1])[0])


@pytest.mark.mc
def test_the_first_melee_hit_does_no_damage_and_an_arrow_does(tiny_world, tmp_path):
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
        for tag, x, n in (("t", 4.5, 1), ("c", 8.5, 5)):  # the target of the dodge, and a control target
            game.command(f'summon zombie {x} {y} 4.5 {{NoAI:1b,IsBaby:0b,UUID:[I;{n},2,3,4],Tags:["{tag}"]}}')
            game.command(f'summon zombie {x + 1} {y} 4.5 {{IsBaby:0b,Tags:["m{tag}"]}}')
            game.command(f"team join p1 @e[tag=m{tag}]")
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag=m{tag},limit=1]", "MILITIA"))
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 0 0 0 0 cavalry -")
        game.command(f'summon zombie 12.5 {y} 12.5 {{NoAI:1b,IsBaby:0b,Tags:["s"]}}')
        game.command(f'summon skeleton 12.5 {y} 2.5 {{NoAI:1b,Tags:["a"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=s]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER"))
        game.command("aoe stats @e[tag=s,limit=1] 1000 0 0 0 0 cavalry -")
        for tag in ("t", "s"):
            assert game.command(f"aoe dodge @e[tag={tag},limit=1] 1 100000 1").strip() == "Dodge: 1 units"   # no refill
        for tag, n in (("t", 1), ("c", 5)):
            assert game.command(f"aoe attack @e[tag=m{tag}] 0000000{n}-0000-0002-0000-000300000004").strip() == "Attack: 1 units"
        time.sleep(7.0)                                   # some hits of each militia (one per AoE2 reload, 2 s)
        game.command("kill @e[tag=mt]")
        game.command("kill @e[tag=mc]")
        lost = {tag: 1000 - health(game, tag) for tag in ("t", "c")}
        hit = lost["c"] / round(lost["c"] / 4) if lost["c"] else 0
        assert lost["c"] >= 8 and lost["t"] == pytest.approx(lost["c"] - hit), lost   # the first hit did no damage
        owner = ",".join(re.findall(r"-?\d+", game.command("data get entity @e[tag=a,limit=1] UUID").split(":", 1)[-1])[:4])
        game.command(f"summon arrow 12.5 {y + 2.5} 12.5 {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
        time.sleep(1.0)
        assert health(game, "s") < 1000                    # a melee dodge lets the arrow pass
