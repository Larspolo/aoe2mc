"""A chakram passes through: it hurts each enemy unit on its line up to Range + 2 tiles with the full damage (AoE2 DE
wiki "Chakram Thrower": "100% pass-through damage", "Pass-through damage": Range + 2 tiles, #1638)."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_ranged import data
from test_siege_walk import summon


@pytest.mark.parametrize("name", ("CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER"))
def test_the_range_command_gives_the_pass_with_the_full_damage(name):
    words = combat.range_command("u", name, 4).split()
    assert words[3] == str(combat.stats(name).range * 4)
    # no blast (the mob throws), the minimum range, the pass in blocks, the part of the damage
    assert words[5:] == ["-", str(combat.MIN_RANGE.get(name, 0) * 4), str(combat.PASS[name] * 4),
                         str(combat.PASS_PART[name])]


def test_the_scorpion_keeps_half_the_damage():
    words = combat.range_command("u", "SCORPION", 4).split()
    part = [str(combat.PASS_PART["SCORPION"])] if "SCORPION" in combat.PASS_PART else []   # none: one half
    assert words[5:] == [str(combat.BLAST.get("SCORPION", 0) * 4), str(combat.MIN_RANGE.get("SCORPION", 0) * 4),
                         str(combat.PASS["SCORPION"] * 4)] + part


@pytest.mark.mc
def test_a_chakram_hurts_the_enemy_militia_on_its_line(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 38} {y - 1} {z0 + 12} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "CHAKRAM_THROWER", x0 + 1.5, y, z0 + 4.5, "chakram")
        c = "@e[tag=chakram,limit=1]"
        # m1 the target, m2 and m3 behind it on the line, o an own militia on the line, f off the line,
        # b past the end of the chakram: 20 + 8 blocks from the thrower
        units = (("m1", 17.5, 4.5, "p2"), ("m2", 21.5, 4.5, "p2"), ("m3", 27.5, 4.5, "p2"), ("o", 24.5, 4.5, "p1"),
                 ("f", 21.5, 7.5, "p2"), ("b", 32.0, 4.5, "p2"))
        for tag, x, z, team in units:
            game.command(f'summon zombie {x0 + x} {y} {z0 + z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry -")   # militia values
        game.command(f"team join p1 {c}")
        assert game.command(combat.stats_command(c, "CHAKRAM_THROWER")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(c, "CHAKRAM_THROWER", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(c, "CHAKRAM_THROWER", 4))
        assert game.command(f"aoe attack {c} @e[tag=m1,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "m3", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        game.command(f"aoe stop {c}")                                             # no second throw
        time.sleep(2)                                                             # the chakram reaches m1
        hp = {t[0]: (data(game, t[0], "Health") or [None])[0] for t in units}
        d = combat.damage("CHAKRAM_THROWER", "MILITIA", t=combat.Stats(1000, 4, 0, 1, 0, 0, {}, ("infantry",)))
        assert hp["m1"] == 1000.0 - d, hp                                         # the attack - 0 melee armor
        assert hp["m2"] == hp["m3"] == 1000.0 - d, hp                             # the full damage behind the target
        assert hp["o"] == hp["f"] == hp["b"] == 1000.0, hp                         # no own unit, off the line, too far
