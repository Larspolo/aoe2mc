"""game/train.py, game/fleet.py, game/combat.py: an own dock trains the cannon galleon in the Imperial Age after
Chemistry (#1484), not for the civilizations without it. It sails into its long range of a building on the shore and
hits it with the AoE2 damage. Values: the AoE2 wiki infobox "Cannon_Galleon" (MediaWiki API, 2026-10-27: Time 46,
Wood 200, Gold 150, HP 120, MAttack 50, +200 vs. buildings, +25 vs. siege, Range 13, MinRange 3, Armor 0/5, ROF 10,
Speed 1.05, LOS 15, AOE 0.25, TrainReq Chemistry) and its availability chart (0 and -1: no cannon galleon)."""
import math
import shutil
import time

import pytest
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

import buildings
from game import civs, combat, fleet, run, train

build = train.build                                                    # the module that train uses
HAVE_NOT = {"ARMENIANS", "AZTECS", "BYZANTINES", "CHINESE", "CUMANS", "DANES", "GOTHS", "HUNS", "INCAS", "JURCHENS",
            "MAPUCHE", "MAYANS", "MUISCA", "ROMANS", "SAXONS", "SHU", "TUPI", "VARANGIANS", "VIKINGS", "WEI", "WU"}


def test_the_cannon_galleon_has_the_aoe2_de_values_of_the_wiki():
    assert train.COSTS["CANNON_GALLEON"] == {"wood": 200, "gold": 150} and train.TRAIN_TIMES["CANNON_GALLEON"] == 46
    assert build.AGE["CANNON_GALLEON"] == 3 and build.NEEDS["CANNON_GALLEON"] == "CHEMISTRY"
    assert "CANNON_GALLEON" in train.TRAINS["DOCK"] and len(train.HELP["CANNON_GALLEON"]) <= 50
    assert combat.stats("CANNON_GALLEON") == (120, 50, 0, 5, 13, 10.0, {"building": 200, "siege": 25},
                                              ("ship", "gunpowder", "warship"))
    assert fleet.SPEEDS["CANNON_GALLEON"] == 1.05 and combat.sight("CANNON_GALLEON") == 15
    assert set(civs.MISSING["CANNON_GALLEON"]) == HAVE_NOT <= set(buildings.CIV_TO_ARCH)


def test_the_cannon_galleon_shoots_far_with_a_blast_and_a_minimum_range():
    assert combat.damage("CANNON_GALLEON", "HOUSE") == 50 + 200 - combat.stats("HOUSE").melee   # melee damage
    assert combat.damage("CANNON_GALLEON", "BOMBARD_CANNON") == 50 - 2 + 25
    shot = combat.range_command("u", "CANNON_GALLEON", 4).split()
    assert shot[3] == "52" and shot[-2:] == ["1.0", "12"]                 # 13 tiles; blast 0.25, minimum range 3 tiles
    assert fleet.reach(dock_map()[1], "CANNON_GALLEON") == 12               # tile size 1: 13 - 1 tiles
    assert train.chemistry("CANNON_GALLEON", combat.stats("CANNON_GALLEON")).attack == 50   # a gunpowder unit


def test_the_dock_menu_has_the_cannon_galleon_after_chemistry():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = set(build.AGE_TECHS[:3]), 300
    slot = train.ITEMS["CANNON_GALLEON"][0]
    train.open_menu(g, "Steve", (15, 12))
    assert f"{slot}:gray_dye:Cannon Galleon:200 wood · 150 gold · 46 s · Needs Chemistry" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, slot) == 0
    g.techs.add("CHEMISTRY")
    train.open_menu(g, "Steve", (15, 12))
    assert f"{slot}:dark_oak_boat:Cannon Galleon:200 wood · 150 gold · 46 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, slot) == 1 and (g.stock["wood"], g.stock["gold"]) == (200, 150)
    assert train.tick(g, 45) == []
    ship, = train.tick(g, 1)
    assert g.soldiers[ship] == "CANNON_GALLEON" and ship in g.ships and g.map.wet(*g.ships[ship].cell)
    assert f"aoe range {ship} 13 118 0.25 3" in server.log                 # tile size 1; 10 s at Normal speed


@pytest.mark.parametrize("civ", ["VIKINGS", "AZTECS", "CHINESE"])
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
    ship, = train.tick(g, 46)
    server.entities["house"] = {"Pos": (2.5, 64.0, 22.5)}                # a house on the land, far from the ship
    goal = fleet.attack(g, {ship}, "house")[ship]
    assert math.dist(goal, (2, 22)) <= fleet.reach(g, "CANNON_GALLEON") and g.map.wet(*goal)
    for _ in range(60):
        fleet.tick(g, 1.0)
    assert not g.ships[ship].path and math.dist(g.ships[ship].cell, (2, 22)) <= 12


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
        assert start - hp(game, house) == 50 + 200 - combat.stats("HOUSE").melee      # one hit, the AoE2 damage
