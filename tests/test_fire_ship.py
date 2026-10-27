"""game/train.py, game/fleet.py, game/combat.py and the plugin: an own dock trains the fire ship and the demolition ship
in the Castle Age (#1440). The fire ship hits an enemy ship from its short range, the demolition ship sails next to its
target, hurts all units in its blast radius, dies and breaks no block. Fake server, and two fights on a server."""
import math
import re
import shutil
import time

import pytest
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import build, combat, fleet, run, train


def test_the_two_ships_have_the_aoe2_de_values_of_the_wiki():
    assert train.COSTS["FIRE_SHIP"] == {"wood": 75, "gold": 45} and train.TRAIN_TIMES["FIRE_SHIP"] == 27
    assert train.COSTS["DEMOLITION_SHIP"] == {"wood": 45, "gold": 80} and train.TRAIN_TIMES["DEMOLITION_SHIP"] == 31
    assert build.AGE["FIRE_SHIP"] == build.AGE["DEMOLITION_SHIP"] == 2                      # the Castle Age
    assert "DEMOLITION_SHIP" in train.TRAINS["DOCK"] and ("FIRE_GALLEY", "FIRE_SHIP") in train.lines("MEDIUM_WARSHIPS")
    assert combat.stats("FIRE_SHIP") == (120, 3, 2, 4, 2.5, 0.25, {"building": 2, "warship": 1}, ("ship", "fireship"))
    assert combat.stats("DEMOLITION_SHIP") == (50, 95, 1, 0, 0, 0.0, {"building": 220}, ("ship",))
    assert fleet.SPEEDS["FIRE_SHIP"] == 1.47 and fleet.SPEEDS["DEMOLITION_SHIP"] == 1.52
    assert combat.sight("FIRE_SHIP") == 5 and combat.sight("DEMOLITION_SHIP") == 6


def test_the_fire_ship_hits_often_with_melee_damage_from_its_short_range():
    assert combat.damage("FIRE_SHIP", "GALLEY") == 3 - 0 + 1                 # melee armor 0, +1 vs. long-range warships
    assert combat.damage("FIRE_SHIP", "FISHING_SHIP") == 3 - 1
    assert combat.range_command("u", "FIRE_SHIP", 4) == "aoe range u 10.0 3 0"   # 2.5 tiles, 0.25 s, only the target
    assert combat.stats_command("u", "FIRE_SHIP").split()[7] == "2"           # ranged with melee damage


def test_the_demolition_ship_blasts_next_to_its_target():
    assert combat.damage("DEMOLITION_SHIP", "GALLEY") == 95 and combat.damage("DEMOLITION_SHIP", "FIRE_SHIP") == 93
    assert combat.damage("DEMOLITION_SHIP", "DOCK") == 95 + 220
    assert combat.range_command("u", "DEMOLITION_SHIP", 4) == "aoe range u 4.0 1 12"   # next to it, 3 tiles of blast
    assert combat.stats_command("u", "DEMOLITION_SHIP").split()[7] == "0"     # melee damage


def test_the_dock_menu_has_the_two_ships_in_the_castle_age():
    server, g = dock_map(wood=400)
    g.techs = {"FEUDAL_AGE"}
    g.stock["gold"] = 200
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "Fire Ship" not in menu                                     # after Medium Warships (#1482)
    assert "4:gray_dye:Demolition Ship:45 wood · 80 gold · 31 s · Needs the Castle Age" in menu
    assert train.order(g, "Steve", DOCK, 4) == 0
    g.techs |= {"CASTLE_AGE", "MEDIUM_WARSHIPS"}
    train.open_menu(g, "Steve", (15, 12))
    assert "6:mangrove_boat:Fire Ship:75 wood · 45 gold · 27 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, 6) == 1 and train.order(g, "Steve", DOCK, 4) == 1
    fire, = train.tick(g, 27)
    demo, = train.tick(g, 31)
    assert (g.soldiers[fire], g.soldiers[demo]) == ("FIRE_SHIP", "DEMOLITION_SHIP")
    assert fire in g.ships and demo in g.ships and g.map.wet(*g.ships[demo].cell)
    assert f"aoe range {demo} 1.0 1 3" in server.log                    # tile size 1: a blast of 3 blocks


def test_a_demolition_ship_sails_next_to_an_enemy_ship():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = {"FEUDAL_AGE", "CASTLE_AGE"}, 200
    train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", DOCK, 4) == 1
    demo, = train.tick(g, 31)
    server.entities["enemy"] = {"Pos": (21.5, 63.0, 2.5)}
    goal = fleet.attack(g, {demo}, "enemy")[demo]
    assert math.dist(goal, (21, 2)) <= fleet.CONTACT and g.map.wet(*goal)
    for _ in range(30):
        fleet.tick(g, 1.0)
    assert not g.ships[demo].path and math.dist(g.ships[demo].cell, (21, 2)) <= fleet.CONTACT


def uuid_of(game, tag):
    ints = [int(i) for i in re.findall(r"-?\d+", game.command(
        f"data get entity @e[tag={tag},limit=1] UUID").rsplit(":", 1)[-1])]
    h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def health(game, uuid):
    out = game.command(f"execute as {uuid} on passengers run data get entity @s Health")
    return float(m[0]) if (m := re.findall(r"(\d+\.?\d*)f", out)) else 0.0


@pytest.mark.mc
def test_a_fire_ship_and_a_demolition_ship_fight_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, T = 200, 4                                                      # a pool in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 50 60")
        game.command(f"fill 0 {y - 1} 0 47 {y} 23 stone_bricks")
        game.command(f"fill 2 {y} 2 45 {y} 21 water")
        game.command(f"clone 0 {y - 1} 0 47 {y} 23 0 {y - 1} 30")      # a copy: the blast breaks no block
        game.command("team add red")
        ids = {}
        for name, tag, x, z in (("FIRE_SHIP", "f", 34.5, 5.5), ("GALLEY", "gg", 40.5, 5.5),     # far from the blast
                                ("DEMOLITION_SHIP", "ddd", 4.5, 14.5), ("GALLEY", "hhhh", 7.5, 14.5),
                                ("FISHING_SHIP", "nnnnn", 11.5, 14.5), ("FISHING_SHIP", "oooooo", 20.5, 14.5)):
            assert "Summoned" in summon(game, name, x, y + 0.5, z, tag), name
            ids[tag] = uuid_of(game, tag)
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], name))     # the crew
            if cmd := combat.range_command(ids[tag], name, T, rate=20):
                assert "Range: 1 units" in game.command(cmd), name
        for tag in ("f", "ddd"):
            game.command(f"team join red @e[tag={tag}]")
            game.command(f"execute as {ids[tag]} on passengers run team join red @s")
        assert "Attack: 1 units" in game.command(f"aoe attack {ids['f']} {ids['gg']}")      # 6 blocks: in its 10
        assert "Attack: 1 units" in game.command(f"aoe attack {ids['ddd']} {ids['hhhh']}")   # 3 blocks: in its reach of 4
        for _ in range(20):
            time.sleep(0.5)
            if "Test failed" in game.command(f"execute if entity {ids['ddd']}"):
                break
        assert "Test failed" in game.command(f"execute if entity {ids['ddd']}")             # the blast: it sank
        assert health(game, ids["hhhh"]) == 110 - 95                                         # the target
        assert "Test failed" in game.command(f"execute if entity {ids['nnnnn']}")           # 4 blocks: 95 - 1 > 50 HP
        assert health(game, ids["oooooo"]) == 50                                             # 13 blocks: out of the blast of 12
        assert "Test passed" in game.command(f"execute if blocks 0 {y - 1} 0 47 {y} 23 0 {y - 1} 30 all")
        assert "Test failed" in game.command(f"execute if entity @e[type=item,x=0,y={y - 5},z=0,dx=48,dy=12,dz=24]")
        time.sleep(3)
        hp = health(game, ids["gg"])
        assert hp < 110 - 4 * 3, hp                                     # 4 damage, about 4 hits per second
        assert "Test passed" in game.command(f"execute if entity {ids['f']}")
