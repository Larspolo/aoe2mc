"""An attack on a siege unit goes to its crew (#3013): the minecart is the target, its crew takes the hits."""
import re
import shutil
import time

import pytest

from game import ai, combat, run
from test_siege_walk import summon


def crew_hp(game, r):
    out = game.command(f"execute as {r} on passengers run data get entity @s Health")
    m = re.search(r"([\d.]+)f", out)
    return float(m.group(1)) if m else None


@pytest.mark.mc
def test_a_militia_attacks_the_crew_of_an_enemy_ram(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    with run.Game(world) as game:
        game.command("forceload add -2 -2 30 24")
        game.command(f"fill 0 {y - 1} 0 29 {y - 1} 21 stone_bricks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "BATTERING_RAM", 10.5, y, 10.5, "r")
        assert "Summoned" in summon(game, "MILITIA", 7.5, y, 10.5, "m")
        r = "@e[type=minecart,tag=r,limit=1]"
        m = "@e[tag=m,limit=1]"
        game.command(f"team join p1 {r}")
        game.command(f"execute as {r} on passengers run team join p1 @s")
        game.command(f"team join p2 {m}")
        assert game.command(combat.stats_command(m, "MILITIA")).strip() == "Stats: 1 units"
        assert game.command(combat.stats_command(r, "BATTERING_RAM")).strip() == "Stats: 1 units"
        game.command(ai.speed_command(m, "MILITIA", 4))
        full = crew_hp(game, r)                  # the crew of the ram has the AoE2 values
        assert full is not None
        assert game.command(f"aoe attack {m} {r}").strip() == "Attack: 1 units"
        end = time.time() + 20
        lost = full
        while time.time() < end and lost >= full:
            time.sleep(0.5)
            lost = crew_hp(game, r)
        assert lost < full, (full, lost)
