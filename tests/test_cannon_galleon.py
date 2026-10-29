"""game/train.py, game/fleet.py, game/combat.py: an own dock trains the cannon galleon in the Imperial Age after
Chemistry (#1484), not for the civilizations without it. It sails into its long range of a building on the shore and
hits it with the AoE2 damage."""
import math
import shutil
import time

import pytest
from test_dock_train import DOCK, dock_map
from test_castle_upgrades import entry
from test_train_archery import menus

import buildings
from game import civs, combat, fleet, run, train

build = train.build                                                    # the module that train uses


def test_the_help_text_is_short_and_the_civilizations_without_it_are_known():
    assert len(train.HELP["CANNON_GALLEON"]) <= 50
    assert set(civs.MISSING["CANNON_GALLEON"]) <= set(buildings.CIV_TO_ARCH)


def test_the_cannon_galleon_shoots_far_with_a_blast_and_a_minimum_range():
    s, h = combat.stats("CANNON_GALLEON"), combat.stats("HOUSE")
    assert combat.damage("CANNON_GALLEON", "HOUSE") == \
        combat.damage("CANNON_GALLEON", "HOUSE", t=h._replace(pierce=h.pierce + 9))   # melee damage: no pierce armor
    shot = combat.range_command("u", "CANNON_GALLEON", 4).split()
    assert shot[3] == str(4 * s.range) and len(shot) == 7                 # the range in blocks, a blast, a minimum range
    assert fleet.reach(dock_map()[1], "CANNON_GALLEON") == s.range - 1    # tile size 1: one tile less
    assert train.chemistry("CANNON_GALLEON", s).attack == s.attack       # a gunpowder unit


def test_the_dock_menu_has_the_cannon_galleon_after_chemistry():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = set(build.AGE_TECHS[:3]), 300
    slot = train.ITEMS["CANNON_GALLEON"][0]
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, (15, 12), "CANNON_GALLEON") + "Needs Chemistry" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, slot) == 0
    g.techs.add("CHEMISTRY")
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, (15, 12), "CANNON_GALLEON") + "queue 0/15" in menus(server)[-1]
    cost, time = train.price(g, "CANNON_GALLEON"), train.seconds(g, "CANNON_GALLEON")
    assert train.order(g, "Steve", DOCK, slot) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (400 - cost.get("wood", 0), 300 - cost.get("gold", 0))
    assert train.tick(g, time - 1) == []
    ship, = train.tick(g, 1)
    assert g.soldiers[ship] == "CANNON_GALLEON" and ship in g.ships and g.map.wet(*g.ships[ship].cell)
    assert combat.range_command(ship, "CANNON_GALLEON", 1) in server.log  # tile size 1


@pytest.mark.parametrize("civ", sorted(civs.MISSING["CANNON_GALLEON"])[:3])
def test_a_civilization_without_it_does_not_see_it(civ):
    server, g = dock_map()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs |= set(build.AGE_TECHS[:3]) | {"CHEMISTRY"}
    train.open_menu(g, "Steve", (15, 12))
    assert "Cannon Galleon" not in menus(server)[-1] and "Fishing Ship" in menus(server)[-1]


def test_a_cannon_galleon_sails_into_its_range_of_a_building_on_the_shore():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = set(build.AGE_TECHS[:3]) | {"CHEMISTRY"}, 300
    train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", DOCK, train.ITEMS["CANNON_GALLEON"][0]) == 1
    ship, = train.tick(g, train.seconds(g, "CANNON_GALLEON"))
    server.entities["house"] = {"Pos": (2.5, 64.0, 22.5)}                # a house on the land, far from the ship
    goal = fleet.attack(g, {ship}, "house")[ship]
    assert math.dist(goal, (2, 22)) <= fleet.reach(g, "CANNON_GALLEON") and g.map.wet(*goal)
    for _ in range(60):
        fleet.tick(g, 1.0)
    assert not g.ships[ship].path and math.dist(g.ships[ship].cell, (2, 22)) <= fleet.reach(g, "CANNON_GALLEON")


@pytest.mark.mc
def test_a_cannon_galleon_hits_a_house_on_the_shore_on_a_server(tiny_world, tmp_path):
    from test_building_damage import hp
    from test_fire_ship import uuid_of
    from test_paper import paper_reachable
    from test_siege_walk import summon
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, T = 200, 4
    with run.Game(world) as game:
        game.command("forceload add -2 -2 80 30")
        game.command(f"fill 0 {y - 1} 0 79 {y} 23 stone_bricks")
        game.command(f"fill 30 {y} 2 77 {y} 21 water")                  # a pool east of the shore at x 30
        house = combat.target_uuid([8, 8, 10, 10])
        for c in combat.building(house, "HOUSE", 2, (8, y + 1, 8, 9, y + 4, 9), T=T):
            game.command(c)
        assert "Summoned" in summon(game, "CANNON_GALLEON", 52.5, y + 0.5, 9.5, "cg")   # 43 blocks: in its 52
        ship = uuid_of(game, "cg")
        assert "Stats: 1 units" in game.command(combat.stats_command(ship, "CANNON_GALLEON"))      # the crew
        assert "Range: 1 units" in game.command(combat.range_command(ship, "CANNON_GALLEON", T, rate=20))
        game.command("team join p1 @e[tag=cg]")
        game.command(f"execute as {ship} on passengers run team join p1 @s")
        start = hp(game, house)
        assert "Attack: 1 units" in game.command(f"aoe attack {ship} {house}")
        end = time.time() + 20
        while time.time() < end and hp(game, house) == start:
            time.sleep(0.1)
        assert start - hp(game, house) == combat.damage("CANNON_GALLEON", "HOUSE")    # one hit, the AoE2 damage
