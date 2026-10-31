"""game/train.py, game/fleet.py and the plugin: an own dock trains a galley in the Feudal Age, and a galley sails into
its range of an enemy ship or a unit on the shore and attacks it (#1386). Fake server, and a fight on a server."""
import math
import re
import shutil
import time

import pytest
from pin_stats import pin
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import combat, fleet, gather, run, train

SLOT = train.ITEMS["GALLEY"][0]


@pytest.fixture(autouse=True)
def galley_range(monkeypatch):
    """Test data: the galley shoots 5 tiles far, the distances of the tests fit it."""
    pin(monkeypatch, "GALLEY", range=5)


def entry(g, name, state, icon=None):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{icon or item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def galley(server, g):
    """A galley of player 1 from the dock, in the Feudal Age."""
    g.techs = {"FEUDAL_AGE"}
    g.stock["gold"] = 100
    rect = train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", rect, SLOT) == 1
    uuid, = train.tick(g, train.seconds(g, "GALLEY"))
    return uuid


def test_a_fishing_ship_does_not_fight():
    assert combat.sight_command("u", "FISHING_SHIP", 4) is None


def test_the_dock_menu_has_the_galley_in_the_feudal_age():
    server, g = dock_map()
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, "GALLEY", "Needs the Feudal Age", "gray_dye") in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, SLOT) == 0
    g.techs = {"FEUDAL_AGE"}
    g.stock["gold"] = 100
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, "GALLEY", "queue 0/15") in menus(server)[-1]
    cost, t = train.COSTS["GALLEY"], train.seconds(g, "GALLEY")
    assert train.order(g, "Steve", DOCK, SLOT) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (200 - cost.get("wood", 0), 100 - cost.get("gold", 0))
    assert train.tick(g, t - 1) == []
    uuid, = train.tick(g, 1)
    assert g.soldiers[uuid] == "GALLEY" and uuid in g.ships and g.map.wet(*g.ships[uuid].cell)
    assert combat.range_command(uuid, "GALLEY", 1) in server.log         # tile size 1


def test_a_galley_sails_into_its_range_of_an_enemy_ship_and_attacks_it():
    server, g = dock_map()
    uuid = galley(server, g)
    server.entities["enemy"] = {"Pos": (21.5, 63.0, 2.5)}             # an enemy ship far in the north-east
    g.select(uuid)
    g.attack("enemy")
    assert f"aoe attack @e[tag={gather.SELECT}] enemy" in server.log   # the plugin gives the target to the crew
    v = g.ships[uuid]
    assert v.prey == "enemy" and v.path and math.dist(v.path[-1], (21, 2)) <= 4 and all(g.map.wet(*c) for c in v.path)
    for _ in range(30):
        fleet.tick(g, 1.0)
    assert not v.path and math.dist(v.cell, (21, 2)) <= 4             # in range (5 tiles less one): it stops there


def test_a_galley_in_range_does_not_sail_and_follows_a_target_that_moves_away():
    server, g = dock_map()
    uuid = galley(server, g)
    v = g.ships[uuid]
    server.entities["enemy"] = {"Pos": (17.5, 63.0, 15.5)}
    assert fleet.attack(g, {uuid}, "enemy") == {} and not v.path       # 2 tiles away: it shoots from its place
    server.entities["enemy"]["Pos"] = (22.5, 63.0, 22.5)
    v.chased = 0.0
    fleet.tick(g, 0.0)
    assert v.path and math.dist(v.path[-1], (22, 22)) <= 4
    del server.entities["enemy"]                                       # it sank
    v.path, v.chased = [], 0.0
    fleet.tick(g, 0.0)
    assert v.prey is None and not v.path


def test_a_galley_attacks_a_unit_on_the_shore_from_the_water():
    server, g = dock_map()
    uuid = galley(server, g)
    server.entities["archer"] = {"Pos": (11.5, 64.0, 20.5)}            # on the land, 3 blocks from the water
    goal = fleet.attack(g, {uuid}, "archer")[uuid]
    assert g.map.wet(*goal) and math.dist(goal, (11, 20)) <= 4


def test_a_move_order_ends_the_attack_and_a_fishing_ship_does_not_attack():
    server, g = dock_map(wood=400)
    uuid = galley(server, g)
    server.entities["enemy"] = {"Pos": (21.5, 63.0, 2.5)}
    fleet.attack(g, {uuid}, "enemy")
    assert g.ships[uuid].prey == "enemy"
    fleet.order(g, {uuid}, (20, 20))
    assert g.ships[uuid].prey is None
    assert train.order(g, "Steve", DOCK, train.ITEMS["FISHING_SHIP"][0]) == 1
    fisher, = train.tick(g, train.seconds(g, "FISHING_SHIP"))
    assert fleet.attack(g, {fisher}, "enemy") == {} and g.ships[fisher].prey is None


@pytest.mark.mc
def test_two_galleys_fight_and_the_loser_sinks_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 26 26")
        game.command(f"fill 0 {y - 1} 0 23 {y} 23 stone_bricks")
        game.command(f"fill 2 {y} 2 21 {y} 21 water")
        ids = {}
        for tag, x in (("a", 4.5), ("bb", 16.5)):   # own UUIDs: tags of other lengths
            assert "Summoned" in summon(game, "GALLEY", x, y + 0.5, 10.5, tag)
            ints = [int(i) for i in re.findall(r"-?\d+", game.command(
                f"data get entity @e[type=oak_boat,tag={tag},limit=1] UUID").rsplit(":", 1)[-1])]
            h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
            ids[tag] = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], "GALLEY"))     # the crew
            assert "Range: 1 units" in game.command(combat.range_command(ids[tag], "GALLEY", 4, rate=20))
        game.command("team add red")
        game.command("team join red @e[tag=a]")
        game.command(f"execute as {ids['a']} on passengers run team join red @s")
        assert "Attack: 1 units" in game.command(f"aoe attack {ids['a']} {ids['bb']}")   # 12 blocks: in its 20
        hp = []
        for _ in range(40):
            time.sleep(0.5)
            out = game.command(f"execute as {ids['bb']} on passengers run data get entity @s Health")
            hp.append(float(m[0]) if (m := re.findall(r"(\d+\.?\d*)f", out)) else 0.0)
            if "Test failed" in game.command(f"execute if entity {ids['bb']}") or "No entity" in out or not out:
                break
        assert hp[0] < 110 and "Test failed" in game.command(f"execute if entity {ids['bb']}"), hp   # it sank
        assert "Test passed" in game.command(f"execute if entity {ids['a']}")
        assert "Test failed" in game.command(f"execute if entity @e[type=item,x=0,y={y - 5},z=0,dx=24,dy=12,dz=24]")
