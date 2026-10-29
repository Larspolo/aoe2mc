"""The castle trains the petard in the Castle Age (#2192, AoE2 DE wiki "Petard (Age of Empires II)"): one blast next
to its target with the AoE2 damage (a bonus vs. walls, gates and castles), then it dies. Fake server; an mc test on
Paper."""
import shutil
import time

import pytest
from menu_line import item
from test_building_damage import hp
from test_siege_walk import summon
from test_train_castle import menus, setup

from game import ai, combat, train


def test_the_castle_trains_the_petard_from_the_castle_age():
    server, g = setup(food=500, gold=500, ages=1)                      # the Feudal Age
    assert "PETARD" in train.trains(g, "CASTLE") and "PETARD" in train.trains(g, "KREPOST")
    train.open_menu(g, "Steve", (12, 4))
    petard = item(menus(server)[-1], "Petard")
    assert petard.split(":")[1] == train.build.LOCKED and petard.endswith(" · Needs the Castle Age")
    assert train.queue(g, "Steve", (12, 4), "PETARD") is None
    server, g = setup(food=500, gold=500)                              # the Castle Age
    assert train.queue(g, "Steve", (12, 4), "PETARD")
    assert {r: 500 - g.stock[r] for r in train.COSTS["PETARD"]} == train.COSTS["PETARD"]


def test_the_petard_blasts_next_to_its_target():
    s = combat.stats("PETARD")
    assert s.range == 0 and "PETARD" in combat.BLAST                   # no range: the reach of a contact blast
    assert combat.range_command("u", "PETARD", 4).split()[3:] == \
        [str(combat.CONTACT * 4), str(round(s.reload / combat.NORMAL * 20)), str(combat.BLAST["PETARD"] * 4)]


@pytest.mark.mc
def test_a_petard_breaks_a_wall_with_one_blast_and_dies(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (16, 200, 8, 19, 203, 11)                            # one wall tile (T = 4) in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 16 {y} 8 19 {y + 3} 11 stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([16, 8, 20, 12])
        wall = combat.wall("STONE_WALL", 2)
        full, hit = wall.hp, combat.damage("PETARD", "STONE_WALL", t=wall)
        for c in combat.building(uuid, "STONE_WALL", 2, box, s=wall):
            game.command(c)
        assert hp(game, uuid) == full
        assert "Summoned" in summon(game, "PETARD", 4.5, y, 9.5, "p")
        p = "@e[tag=p,limit=1]"
        game.command(f"team join p1 {p}")
        assert game.command(combat.stats_command(p, "PETARD")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(p, "PETARD", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(p, "PETARD", 4))
        assert game.command(f"aoe attack {p} {uuid}").strip() == "Attack: 1 units"
        end = time.time() + 30
        while time.time() < end and hp(game, uuid) == full:
            time.sleep(0.2)
        time.sleep(3)                                                  # no second blast
        assert hp(game, uuid) == full - hit
        assert "Test failed" in game.command(f"execute if entity {p}")    # it died in its blast
        assert "Test passed" in game.command(f"execute if block 10 {y - 1} 9 stone_bricks")   # no vanilla explosion
