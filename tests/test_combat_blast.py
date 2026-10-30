"""The Mangonel line hits all units in its AoE2 blast radius around the target (#1050)."""
import shutil
import time

import pytest
from test_ranged import data
from test_siege_walk import summon

from game import ai, combat, run


def test_the_range_command_gives_the_blast_in_blocks():
    s = combat.stats("ONAGER")
    assert combat.range_command("u", "ONAGER", 4).split()[3:6] == [
        str(s.range * 4), str(round(s.reload / combat.NORMAL * 20)), str(combat.BLAST["ONAGER"] * 4)]
    assert combat.range_command("u", "SIEGE_ONAGER", 2).split()[5] == str(combat.BLAST["SIEGE_ONAGER"] * 2)   # then the minimum range (#1350)
    assert len(combat.range_command("u", "ARCHER", 4).split()) == 5           # no blast: one target


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
        d = combat.damage("ONAGER", "MILITIA", t=combat.Stats(1000, 4, 0, 1, 0, 0, {}, ("infantry",)))
        assert hp["m1"] == hp["m2"] < 1000.0 and (1000.0 - hp["m1"]) % d == 0, hp      # d per shot on each one
        assert hp["m3"] == 1000.0, hp                                                 # outside the blast
