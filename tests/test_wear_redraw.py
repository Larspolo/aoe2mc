"""game/build.py: a wall technology redraws a damaged wall, and `aoe unwear` makes the damage stages of the plugin
keep the blocks of the new design, not of the old one (#3071)."""
import inspect
import math
import shutil
import types

import pytest
from test_build_gates import line
from test_build_site import site_map

from game import build, combat, run


def upgraded(redraw):
    server, g = site_map(wood=200, chosen=0)
    g.stock["stone"] = 100
    line(g, (15, 6), (15, 11))
    site = build.gate(g, "Steve", "GATE", (15, 7))
    build.rise(g, site, math.inf)
    server.log.clear()
    g.techs, command = {"FEUDAL_AGE", "CASTLE_AGE", "FORTIFIED_WALL"}, g.command
    g.command = lambda c: "Gate has 1000 [aoe_hp]" if c.startswith("scoreboard players get") else command(c)
    build.upgrade(g, site, types.SimpleNamespace(hp=1650), redraw=redraw)
    return server.log


def test_the_redraw_sends_unwear_after_the_blocks_and_before_the_hit_points():
    log = upgraded(True)
    unwear = [i for i, c in enumerate(log) if c.startswith("aoe unwear ")]
    hp = [i for i, c in enumerate(log) if " aoe_hp " in c and c.startswith("scoreboard players set")]
    draw = [i for i, c in enumerate(log) if c.startswith(("fill ", "setblock "))]
    assert len(unwear) == 1 and draw and hp
    assert max(draw) < unwear[0] < hp[0]


def test_no_redraw_and_retower_do_not_send_unwear():
    assert not any(c.startswith("aoe unwear") for c in upgraded(False))
    assert "unwear" not in inspect.getsource(build.retower)


@pytest.mark.mc
def test_the_damage_stages_keep_the_new_design_after_unwear(tiny_world, tmp_path):
    from test_building_wear import blocks, settle
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    box = (8, y, 8, 15, y + 5, 15)
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 23 {y - 1} 23 stone")
        game.command(f"fill 8 {y} 8 15 {y + 5} 15 stone_bricks hollow")
        game.command(f"fill 9 {y + 1} 9 14 {y + 4} 14 barrier")
        game.command("team add p2")
        uuid = combat.target_uuid([8, 8, 16, 16])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        full = blocks(game, box)
        game.command(f"scoreboard players set {uuid} aoe_hp 300")      # stage 3 of 550
        worn = settle(game, box, full)
        assert worn != full
        game.command(f"fill 8 {y} 8 15 {y + 5} 15 oak_planks hollow")  # the redraw of build.upgrade
        game.command(f"aoe unwear {uuid}")
        game.command(f"scoreboard players set {uuid} aoe_hp 450")      # stage 1
        settle(game, box, blocks(game, box))
        game.command(f"scoreboard players set {uuid} aoe_hp 550")      # full
        now = settle(game, box, blocks(game, box))
        assert not {"stone_bricks", "cracked_stone_bricks"} & set(now.values()), now
