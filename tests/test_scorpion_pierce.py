"""A Scorpion bolt passes through: it hurts the enemy units on its line up to Range + 2 tiles with half the damage (#1401)."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_ranged import data
from test_siege_walk import summon


@pytest.mark.parametrize("name", ("SCORPION", "HEAVY_SCORPION"))
def test_a_scorpion_range_command_gives_the_pass_in_blocks(name):
    words = combat.range_command("u", name, 4).split()
    assert words[5:] == ["0", str(combat.MIN_RANGE[name] * 4), str(combat.PASS[name] * 4)]   # blast 0, minimum range, pass


@pytest.mark.mc
def test_a_scorpion_bolt_hurts_the_enemy_militia_on_its_line(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 44} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 42} {y - 1} {z0 + 12} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "SCORPION", x0 + 1.5, y, z0 + 4.5, "s")
        s = "@e[type=minecart,tag=s,limit=1]"
        # m1 the target, m2 and m3 behind it on the line, o an own militia on the line, f off the line,
        # b past the end of the bolt: 28 + 8 blocks from the scorpion
        units = (("m1", 18.5, 4.5, "p2"), ("m2", 22.5, 4.5, "p2"), ("m3", 30.5, 4.5, "p2"), ("o", 26.5, 4.5, "p1"),
                 ("f", 22.5, 7.5, "p2"), ("b", 40.0, 4.5, "p2"))
        for tag, x, z, team in units:
            game.command(f'summon zombie {x0 + x} {y} {z0 + z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry -")   # militia values
        game.command(f"team join p1 {s}")
        assert game.command(combat.stats_command(s, "SCORPION")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(s, "SCORPION", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(s, "SCORPION", 4))
        assert game.command(f"aoe attack {s} @e[tag=m1,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "m1", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        game.command(f"aoe stop {s}")                                             # no second shot
        time.sleep(0.5)
        hp = {t[0]: (data(game, t[0], "Health") or [None])[0] for t in units}
        v = combat.stats("SCORPION")
        hit = v.attack + v.bonus.get("infantry", 0) - 1                            # 1 pierce armor
        assert hp["m1"] == 1000.0 - hit, hp
        assert hp["m2"] == hp["m3"] == 1000.0 - hit / 2, hp                       # half the damage behind the target
        assert hp["o"] == hp["f"] == hp["b"] == 1000.0, hp                         # no own unit, off the line, too far
