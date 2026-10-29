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

from game import combat, fleet, run, train


def entry(g, name, state, icon=None):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{icon or item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def test_the_fire_ship_hits_with_melee_damage_from_its_range():
    s = combat.stats("FIRE_SHIP")
    assert combat.range_command("u", "FIRE_SHIP", 4).startswith(f"aoe range u {s.range * 4} ")   # only the target
    assert combat.stats_command("u", "FIRE_SHIP").split()[7] == "2"           # ranged with melee damage


def test_the_demolition_ship_blasts_next_to_its_target():
    assert combat.range_command("u", "DEMOLITION_SHIP", 4).split()[-1] == str(combat.BLAST["DEMOLITION_SHIP"] * 4)
    assert combat.stats_command("u", "DEMOLITION_SHIP").split()[7] == "0"     # melee damage


def test_the_dock_menu_has_the_two_ships_in_the_castle_age():
    server, g = dock_map(wood=400)
    g.techs = {"FEUDAL_AGE"}
    g.stock["gold"] = 200
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "Fire Ship" not in menu                                     # after Medium Warships (#1482)
    assert "Demolition Ship" not in menu                                # after its upgrade (#1483)
    g.techs |= {"CASTLE_AGE", "MEDIUM_WARSHIPS", "DEMOLITION_SHIP_UPGRADE"}
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, "FIRE_SHIP", "queue 0/15") in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, train.ITEMS["FIRE_SHIP"][0]) == 1
    assert train.order(g, "Steve", DOCK, train.ITEMS["DEMOLITION_SHIP"][0]) == 1
    fire, = train.tick(g, train.seconds(g, "FIRE_SHIP"))
    demo, = train.tick(g, train.seconds(g, "DEMOLITION_SHIP"))
    assert (g.soldiers[fire], g.soldiers[demo]) == ("FIRE_SHIP", "DEMOLITION_SHIP")
    assert fire in g.ships and demo in g.ships and g.map.wet(*g.ships[demo].cell)
    assert combat.range_command(demo, "DEMOLITION_SHIP", 1) in server.log   # tile size 1: the blast in blocks


def test_a_demolition_ship_sails_next_to_an_enemy_ship():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = {"FEUDAL_AGE", "CASTLE_AGE", "DEMOLITION_SHIP_UPGRADE"}, 200
    train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", DOCK, train.ITEMS["DEMOLITION_SHIP"][0]) == 1
    demo, = train.tick(g, train.seconds(g, "DEMOLITION_SHIP"))
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
