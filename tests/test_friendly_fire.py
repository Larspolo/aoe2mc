"""game/civs.py: Jurchen military units take less friendly fire, the blast of an own or allied unit (#2418). The plugin
gets the factor with "aoe stats"."""
import shutil
import time

import pytest

from game import ai, combat, run, train

from test_civ_work import setup
from test_ranged import data
from test_siege_walk import summon


def test_the_friendly_fire_factor_changes_no_combat_value():
    assert train.stats(setup("JURCHENS"), "MAN_AT_ARMS") == train.stats(setup("CHINESE"), "MAN_AT_ARMS")


def test_the_plugin_gets_the_factor_of_the_friendly_fire():
    s = combat.stats("KNIGHT")
    assert combat.stats_command("u", "KNIGHT", s, 1.0, 0.5).endswith(" 1 0.5")   # the reload, then the bonus damage factor 1
    assert combat.stats_command("u", "KNIGHT", s, 0.6, 0.5).endswith(" 0.6 0.5")
    assert combat.stats_command("u", "KNIGHT", s, 1.0, 1.0) == combat.stats_command("u", "KNIGHT")   # 1: no field


@pytest.mark.mc
def test_an_onager_blast_hurts_an_own_jurchen_unit_half(tiny_world, tmp_path):
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
        # the target (an enemy) and two own militia in the blast (5 blocks): one with the Jurchen factor 0.5
        for tag, x, z, team, friendly in (("e", 20.5, 4.5, "p2", ""), ("j", 20.5, 5.5, "p1", " 1 0.5"),
                                          ("c", 21.5, 4.5, "p1", "")):
            game.command(f'summon zombie {x0 + x} {y} {z0 + z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry - 20{friendly}").strip() \
                == "Stats: 1 units"
        game.command(f"team join p1 {o}")
        assert game.command(combat.stats_command(o, "ONAGER")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(o, "ONAGER", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(o, "ONAGER", 4))
        assert game.command(f"aoe attack {o} @e[tag=e,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "j", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        time.sleep(0.5)
        hp = {t: (data(game, t, "Health") or [None])[0] for t in ("e", "j", "c")}
        shots = round((1000.0 - hp["c"]) / 55)
        assert shots >= 1 and hp["e"] == hp["c"] == 1000.0 - 55 * shots, hp           # 55 per shot, also on an own unit
        assert hp["j"] == 1000.0 - 27.5 * shots, hp                                     # half for the Jurchen unit
