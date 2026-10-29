"""The ranged siege units without a blast (Scorpion, Trebuchet, Organ Gun ...) shoot their target only (#1062)."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_ranged import data
from test_siege_walk import summon

SHOOTERS = ("SCORPION", "HEAVY_SCORPION", "TREBUCHET", "BOMBARD_CANNON", "ORGAN_GUN", "ROCKET_CART")


@pytest.mark.parametrize("name", SHOOTERS)
def test_each_ranged_siege_unit_gets_a_siege_range(name):
    words = combat.range_command("u", name, 4).split()
    assert len(words) == 6 + (name in combat.MIN_RANGE) + (name in combat.PASS) and float(words[3]) == combat.stats(name).range * 4
    assert float(words[5]) == combat.BLAST.get(name, 0) * 4                    # blast 0: the target only


def test_the_bombard_cannon_has_its_blast_and_a_ram_does_not_shoot():
    assert combat.range_command("u", "BOMBARD_CANNON", 4).split()[5] == str(combat.BLAST["BOMBARD_CANNON"] * 4)   # then the minimum range (#1350)
    ram = round(combat.stats("BATTERING_RAM").reload / combat.NORMAL * 20)
    assert combat.range_command("u", "BATTERING_RAM", 4).split()[3:] == [str(combat.RAM_REACH), str(max(1, ram)), "0"]   # melee reach (#1399)
    assert len(combat.range_command("u", "ARCHER", 4).split()) == 5           # not a minecart: no siege shot


@pytest.mark.mc
def test_a_scorpion_shot_hurts_only_its_militia(tiny_world, tmp_path):
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
        assert "Summoned" in summon(game, "SCORPION", x0 + 1.5, y, z0 + 4.5, "s")
        s = "@e[type=minecart,tag=s,limit=1]"
        for tag, x, z in (("m1", 18.5, 4.5), ("m2", 18.5, 5.5)):   # m2 next to m1: no blast, no damage
            game.command(f'summon zombie {x0 + x} {y} {z0 + z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry -")   # militia values
        game.command(f"team join p1 {s}")
        assert game.command(combat.stats_command(s, "SCORPION")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(s, "SCORPION", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(s, "SCORPION", 4))
        assert game.command(f"aoe attack {s} @e[tag=m1,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "m1", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        time.sleep(0.5)
        hp = {t: (data(game, t, "Health") or [None])[0] for t in ("m1", "m2")}
        d = combat.damage("SCORPION", "MILITIA", t=combat.Stats(1000, 4, 0, 1, 0, 0, {}, ("infantry",)))
        assert hp["m1"] < 1000.0 and (1000.0 - hp["m1"]) % d == 0, hp           # the attack - 1 pierce armor per shot
        assert hp["m2"] == 1000.0, hp
