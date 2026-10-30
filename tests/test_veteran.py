"""The Jaguar Warrior gets +1 attack for each unit that it kills, up to +4 (#4467, AoE2 wiki "Jaguar Warrior": "Gains
+1 attack for each unit killed (up to 4)"): the key "veteran", game/abilities/veteran.py and `aoe veteran` of the plugin.
Test data, and kills on a server."""
import re
import shutil
import time

import pytest
from abilities import veteran

from game import combat, run


def test_the_veteran_command_gives_the_attack_and_the_max(monkeypatch):
    monkeypatch.setattr(veteran, "UNITS", {"MILITIA": {"attack": 1, "max": 4}})
    assert veteran.command("u-1", "MILITIA") == "aoe veteran u-1 1 4"
    assert veteran.command("u-1", "ARCHER") is None


def uuid(n):
    return f"{n:08x}-0000-0002-0000-000300000004"          # the UUID [I;n,2,3,4]


def health(game, n):
    out = game.command(f"data get entity {uuid(n)} Health")
    found = re.findall(r"-?\d+\.?\d*", out.split(":", 1)[-1])
    return float(found[0]) if found and "No entity" not in out else 0.0     # a dead unit: 0


def first_loss(game, attacker, n, timeout=8.0):
    """Order the attacker on unit n; the hit points that its first hit takes (all of them for a unit that dies)."""
    before = health(game, n)
    assert game.command(f"aoe attack @e[tag={attacker}] {uuid(n)}").strip() == "Attack: 1 units"
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(0.1)
        if (now := health(game, n)) < before:
            return before - now
    raise AssertionError(f"no hit on {n}")


@pytest.mark.mc
def test_two_kills_give_2_more_damage_and_six_kills_give_4(tiny_world, tmp_path):
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
        for n in range(1, 11):                            # 1, 2: the big targets; 3 to 10: the victims
            x, z = (3.5 + (n - 1) * 9, 11.5) if n <= 2 else (n + 0.5, 7.5)    # apart: no zombie blocks a path
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,UUID:[I;{n},2,3,4],Tags:["t"]}}')
            game.command(f"aoe stats {uuid(n)} {1000 if n <= 2 else 1} 0 0 0 0 cavalry -")
        game.command("team join p2 @e[tag=t]")
        for tag, x in (("v", 3.5), ("c", 12.5)):          # the veteran and a control unit
            game.command(f'summon zombie {x} {y} 4.5 {{IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p1 @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA"))
        assert game.command("aoe veteran @e[tag=v,limit=1] 1 4").strip() == "Veteran: 1 units"
        first = first_loss(game, "c", 2)
        for n in (3, 4):
            first_loss(game, "v", n)
        assert first_loss(game, "v", 1) == pytest.approx(first + 2)
        for n in (5, 6, 7, 8):
            first_loss(game, "v", n)
        time.sleep(2.5)                                   # one AoE2 reload: the next hit on unit 1 is a new one
        assert first_loss(game, "v", 1) == pytest.approx(first + 4)
