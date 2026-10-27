"""The Mangonel line hits all units in its AoE2 blast radius around the target (#1050)."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_ranged import data
from test_siege_walk import summon


def test_the_mangonel_line_has_the_blast_radius_of_the_wiki():
    assert combat.BLAST == {"BOMBARD_CANNON": 0.5, "HEAVY_ROCKET_CART": 1.25, "HOUFNICE": 0.7,   # tiles, AoE2 DE
                            "MANGONEL": 1.0, "ONAGER": 1.25, "ROCKET_CART": 1.0, "SIEGE_ONAGER": 1.5,   # ("AOE")
                            "DEMOLITION_SHIP": 3, "FIRE_SHIP": 0,                                      # (#1440)
                            "CANNON_GALLEON": 0.25,                                                    # (#1484)
                            "DEMOLITION_RAFT": 2.5,                                                    # (#1481)
                            "ELITE_CANNON_GALLEON": 0.3,                                               # (#1491)
                            "FAST_FIRE_SHIP": 0, "HEAVY_DEMOLITION_SHIP": 3.25,                         # (#1483)
                            "FIRE_GALLEY": 0}


def test_the_range_command_gives_the_blast_in_blocks():
    assert combat.range_command("u", "ONAGER", 4).split()[3:6] == ["32", str(round(6.0 / 1.7 * 20)), "5.0"]
    assert combat.range_command("u", "SIEGE_ONAGER", 2).split()[5] == "3.0"          # then the minimum range (#1350)
    assert len(combat.range_command("u", "ARCHER", 4).split()) == 5           # no blast: one target


def test_each_unit_in_the_blast_takes_the_damage_rule():
    assert combat.damage("ONAGER", "MILITIA") == 55                           # melee armor 0
    assert combat.damage("ONAGER", "BATTERING_RAM") == 55 + 3 + 12


@pytest.mark.mc
def test_an_onager_shot_hits_two_militia_next_to_each_other(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 12} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "ONAGER", x0 + 1.5, y, z0 + 4.5, "o")
        o = "@e[type=minecart,tag=o,limit=1]"
        # two militia 1 block apart (blast 5 blocks), a third one 10 blocks away
        for tag, x, z in (("m1", 20.5, 4.5), ("m2", 20.5, 5.5), ("m3", 20.5, 14.5)):
            game.command(f'summon zombie {x0 + x} {y} {z0 + z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry -")   # militia values, many hit points
        game.command(f"team join p1 {o}")
        assert game.command(combat.stats_command(o, "ONAGER")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(o, "ONAGER", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(o, "ONAGER", 4))
        assert game.command(f"aoe attack {o} @e[tag=m1,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "m2", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        time.sleep(0.5)
        hp = {t: (data(game, t, "Health") or [None])[0] for t in ("m1", "m2", "m3")}
        assert hp["m1"] == hp["m2"] < 1000.0 and (1000.0 - hp["m1"]) % 55 == 0, hp     # 55 per shot on each one
        assert hp["m3"] == 1000.0, hp                                                 # outside the blast
