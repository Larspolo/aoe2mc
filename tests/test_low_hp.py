"""The Jian Swordsman switches to its unshielded form below 45 HP (#4472, AoE2 DE wiki "Jian Swordsman"): the key
"low_hp" of data/units.jsonl, combat.low_hp_command and `aoe lowhp`. Test data, and arrows on a server."""
import re
import shutil
import time

import pytest

from game import combat, run


def test_low_hp_command_gives_the_form_of_the_data(monkeypatch):
    monkeypatch.setattr(combat, "LOW_HP", {"MILITIA": {"hp": 20, "melee": 1, "pierce": 0, "speed": 1.25}})
    assert combat.low_hp_command("u-1", "MILITIA") == "aoe lowhp u-1 20 1 0 1.25"
    assert combat.low_hp_command("u-1", "ARCHER") is None


def value(out):
    return float(re.findall(r"-?\d+\.?\d*", out.split(":", 1)[-1] if ":" in out else out)[-1])


@pytest.mark.mc
def test_the_low_form_takes_more_arrow_damage_and_is_faster(tiny_world, tmp_path):
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
        game.command(f'summon zombie 4.5 {y} 4.5 {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command(f'summon skeleton 12.5 {y} 12.5 {{NoAI:1b,Tags:["a"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        game.command("aoe stats @e[tag=a,limit=1] 30 10 0 0 1 archer -")
        game.command("aoe stats @e[tag=t,limit=1] 50 0 0 5 0 infantry -")
        assert game.command("aoe lowhp @e[tag=t,limit=1] 45 0 2 1.1").strip() == "Low HP: 1 units"
        owner = ",".join(re.findall(r"-?\d+", game.command("data get entity @e[tag=a,limit=1] UUID").split(":", 1)[-1])[:4])

        def shoot():
            before = value(game.command("data get entity @e[tag=t,limit=1] Health"))
            game.command(f"summon arrow 4.5 {y + 2.5} 4.5 {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
            time.sleep(1.0)
            return before - value(game.command("data get entity @e[tag=t,limit=1] Health"))

        def speed():
            return (value(game.command("attribute @e[tag=t,limit=1] minecraft:movement_speed get"))
                    / value(game.command("attribute @e[tag=t,limit=1] minecraft:movement_speed base get")))

        assert shoot() == pytest.approx(5)                # 10 - 5 pierce: 50 -> 45, not below 45
        assert speed() == pytest.approx(1)
        assert shoot() == pytest.approx(5)                # 45 -> 40: now the low form
        assert speed() == pytest.approx(1.1, abs=0.01)
        assert shoot() == pytest.approx(8)                # 10 - 2 pierce
        game.command("data modify entity @e[tag=t,limit=1] Health set value 50f")
        time.sleep(0.5)
        assert speed() == pytest.approx(1)
        assert shoot() == pytest.approx(5)                # the normal form again
