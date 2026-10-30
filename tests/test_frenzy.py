"""The Temple Guard attacks faster the longer it fights (#4468, AoE2 DE wiki "Temple Guard": "Every attack of the
Temple Guard decreases its attack reload time by 0.2 seconds for 5 seconds"): the key "frenzy",
game/abilities/frenzy.py and `aoe frenzy` of the plugin. Test data, and melee hits on a server."""
import re
import shutil
import time

import pytest
from abilities import frenzy

from game import run


def test_the_frenzy_command_gives_the_values_in_ticks(monkeypatch):
    monkeypatch.setattr(frenzy, "UNITS", {"MILITIA": {"less": 0.2, "time": 5, "min": 1}})
    assert frenzy.command("u-1", "MILITIA") == "aoe frenzy u-1 4 100 20"
    assert frenzy.command("u-1", "ARCHER") is None


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    return float(re.findall(r"-?\d+\.?\d*", out.split(":", 1)[-1])[0])


def tick(game):
    return int(re.findall(r"\d+", game.command("time query gametime"))[-1])


@pytest.mark.mc
def test_the_gaps_between_the_hits_get_shorter_down_to_the_minimum(tiny_world, tmp_path):
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
        game.command(f'summon zombie 4.5 {y} 4.5 {{NoAI:1b,IsBaby:0b,UUID:[I;1,2,3,4],Tags:["t"]}}')
        game.command(f'summon zombie 5.5 {y} 4.5 {{IsBaby:0b,Tags:["m"]}}')
        game.command("team join p1 @e[tag=m]")
        game.command("team join p2 @e[tag=t]")
        game.command("aoe stats @e[tag=m,limit=1] 40 4 0 1 0 infantry - 40")   # a reload of 40 ticks
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 cavalry -")
        assert game.command("aoe frenzy @e[tag=m,limit=1] 4 100 20").strip() == "Frenzy: 1 units"
        assert game.command("aoe attack @e[tag=m] 00000001-0000-0002-0000-000300000004").strip() == "Attack: 1 units"
        hits, last, end = [], 1000.0, time.time() + 15
        while time.time() < end:
            if (hp := health(game, "t")) < last:
                hits.append(tick(game))
                last = hp
            time.sleep(0.02)
        gaps = [b - a for a, b in zip(hits, hits[1:])]
        assert len(gaps) >= 8, gaps
        # 40, 36, 32, then 28: 3 hits of the last 100 ticks (the rule of the wiki settles at 1.4 s from a 2 s reload)
        assert gaps[0] >= 34 and gaps[-1] <= 30 and min(gaps) >= 18, gaps
