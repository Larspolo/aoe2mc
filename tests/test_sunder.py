"""Each hit of the Obuch lowers the melee and the pierce armor of the target by 1, down to 0 (#4466, AoE2 wiki "Obuch":
"Reduces armor and pierce armor of units by 1 (cannot be reduced below 0) each with every attack"): the key "sunder",
combat.sunder_command and `aoe sunder` of the plugin. Test data, and hits on a server."""
import re
import shutil
import time

import pytest

from game import combat, run


def test_the_sunder_command_gives_the_armor_less_per_hit(monkeypatch):
    monkeypatch.setattr(combat, "SUNDER", {"MILITIA": 1})
    assert combat.sunder_command("u-1", "MILITIA") == "aoe sunder u-1 1"
    assert combat.sunder_command("u-1", "ARCHER") is None


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    return float(re.findall(r"-?\d+\.?\d*", out.split(":", 1)[-1])[0])


def loss(game, tag, timeout=8.0):
    """The hit points that the next hit on the unit with the tag takes."""
    before, end = health(game, tag), time.time() + timeout
    while time.time() < end:
        time.sleep(0.1)
        if (now := health(game, tag)) < before:
            return before - now
    raise AssertionError(f"no hit on {tag}")


@pytest.mark.mc
def test_each_hit_lowers_the_melee_and_the_pierce_armor(tiny_world, tmp_path):
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
        game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command(f'summon zombie {x + 1.5} {y} {z} {{IsBaby:0b,Tags:["o"]}}')
        game.command(f'summon skeleton 12.5 {y} 12.5 {{NoAI:1b,Tags:["a"]}}')
        game.command("team join p2 @e[tag=t]")
        game.command("team join p1 @e[tag=o]")
        game.command("team join p1 @e[tag=a]")
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 2 1 0 cavalry -")
        game.command("aoe stats @e[tag=o,limit=1] 100 4 0 0 0 infantry -")    # attack 4, no bonus
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER"))
        assert game.command("aoe sunder @e[tag=o,limit=1] 1").strip() == "Sunder: 1 units"
        assert game.command("aoe attack @e[tag=o] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        hits = [loss(game, "t") for _ in range(4)]        # melee armor 2, 1, 0, 0
        assert hits == [2.0, 3.0, 4.0, 4.0], hits
        game.command("kill @e[tag=o]")
        archer = combat.STATS["ARCHER"].attack
        owner = ",".join(re.findall(r"-?\d+", game.command("data get entity @e[tag=a,limit=1] UUID").split(":", 1)[-1]))
        game.command(f"summon arrow {x} {y + 2.5} {z} {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
        assert loss(game, "t") == float(archer)           # pierce armor 0, no class bonus of the archer on cavalry
