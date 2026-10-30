"""The charged shot of the Bolas Rider (#4548, AoE2 DE wiki "Bolas Rider": "Fires a projectile shot every 30 seconds
that has +2 (+3 Elite) attack and slows targets by 15% for 10 seconds"): the key "snare", game/abilities/snare.py and
`aoe snare` of the plugin. Test data, fake server of test_gather, and arrows on a server."""
import re
import shutil
import time

import pytest
from abilities import snare as ability
from test_kill_spoils import game

from game import combat, gather, run, train

SNARE = {"time": 30, "attack": 2, "slow": 0.15, "for": 10}


def snare(monkeypatch):
    monkeypatch.setattr(ability, "UNITS", {"KNIGHT": SNARE})


def test_a_new_unit_with_the_key_gets_its_charged_shot(monkeypatch):
    snare(monkeypatch)
    server, g = game("FRANKS")
    u = train.summon(g, "KNIGHT", (8.5, 64.0, 8.5))
    ticks = [round(SNARE[k] / gather.NORMAL * 20) for k in ("time", "for")]
    assert f"aoe snare {u} {ticks[0]} {SNARE['attack']} 0 {ticks[1]}" in server.log


def test_a_unit_without_the_key_gets_none(monkeypatch):
    snare(monkeypatch)
    server, g = game("FRANKS")
    train.summon(g, "MILITIA", (8.5, 64.0, 8.5))
    assert not any(c.startswith("aoe snare") for c in server.log)
    assert ability.command("u", "MILITIA") is None


@pytest.mark.mc
def test_the_first_charged_hit_slows_the_target_and_the_next_does_not(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x, y, z = 4.5, 200, 4.5
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
        assert game.command("aoe snare @e[tag=a,limit=1] 100000 2 0 200").strip() == "Snare: 1 units"
        owner = ",".join(re.findall(r"-?\d+", game.command("data get entity @e[tag=a,limit=1] UUID").split(":", 1)[-1])[:4])
        slow = []
        for _ in range(2):                                 # an arrow of the archer falls on the target
            game.command(f"summon arrow {x} {y + 2.5} {z} {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
            time.sleep(1.0)
            slow.append("slowness" in game.command("data get entity @e[tag=t,limit=1] active_effects"))
            game.command("effect clear @e[tag=t]")
        assert slow == [True, False]
