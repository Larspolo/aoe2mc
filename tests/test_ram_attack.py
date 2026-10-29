"""A ram walks to an enemy building and hits it (#1399): its carrier pig gets the range goal with the reach of a melee
hit (combat.RAM_REACH), so it walks with Minecraft path finding and hits once per AoE2 reload."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_building_damage import hp
from test_siege_walk import summon


def test_a_ram_gets_the_reach_of_a_melee_hit():
    reload = combat.stats("CAPPED_RAM").reload
    assert combat.range_command("u", "CAPPED_RAM", 4).split()[3:] == \
        [str(combat.RAM_REACH), str(round(reload / combat.NORMAL * 20)), "0"]
    assert combat.range_command("u", "SIEGE_TOWER", 4) is None                 # no attack
    assert combat.range_command("u", "MILITIA", 4) is None                     # not a siege unit


@pytest.mark.mc
def test_a_ram_walks_to_a_barracks_and_hits_it(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (20, 200, 8, 25, 240, 13)                            # a barracks in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 30 24")
        game.command(f"fill 0 {y - 1} 0 29 {y - 1} 21 stone_bricks")
        game.command(f"fill 20 {y} 8 25 {y + 3} 13 oak_planks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([20, 8, 26, 14])
        for c in combat.building(uuid, "BARRACKS", 2, box):
            game.command(c)
        full = hp(game, uuid)
        assert "Summoned" in summon(game, "BATTERING_RAM", 3.5, y, 10.5, "r")
        r = "@e[type=minecart,tag=r,limit=1]"
        game.command(f"team join p1 {r}")
        assert game.command(combat.stats_command(r, "BATTERING_RAM")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(r, "BATTERING_RAM", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(r, "BATTERING_RAM", 4))
        assert game.command(f"aoe attack {r} {uuid}").strip() == "Attack: 1 units"
        seen, end = [(time.time(), full)], time.time() + 60
        while time.time() < end and len(seen) < 3:
            if (h := hp(game, uuid)) != seen[-1][1]:
                seen.append((time.time(), h))
            time.sleep(0.1)
        d = combat.damage("BATTERING_RAM", "BARRACKS")
        assert [h for _, h in seen] == [full, full - d, full - 2 * d], seen     # combat.damage per hit
        gap, step = seen[2][0] - seen[1][0], combat.stats("BATTERING_RAM").reload / combat.NORMAL
        assert 0.8 * step < gap < 1.5 * step, seen                            # one hit per reload
