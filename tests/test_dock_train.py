"""game/train.py and game/fleet.py: an own dock trains a fishing ship, and a selected ship sails on the water (#1383).
Fake server, no Minecraft."""
import math
import re
import shutil
import time
import types

import pytest
from test_build_site import Server
from test_gather import grid
from test_train_archery import menus

from game import fleet, gather, run, train

DOCK = (14, 17, 11, 14)                                                # block footprint (x0, x1, z0, z1)


def dock_map(wood=200):
    """A flat 24 x 24 map (tile size 1): land at x < 14 (y 64), water at x >= 14 (its surface at y 63), a dock of
    player 1 on the water at the shore."""
    rows = [[64] * 14 + ["-"] * 10 for _ in range(24)]
    data = grid(rows, [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
                       {"kind": "building", "name": "DOCK", "player": 1, "tile": [15.5, 12.5], "footprint": [14, 11, 17, 14]}])
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = Server({"Steve": {"Pos": (12.5, 64.0, 12.5), "Rotation": (-90.0, 40.0)}})
    g = gather.Gather(server, data).setup()
    g.stock["wood"] = wood
    return server, g


def trained(server, g):
    rect = train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", rect, train.ITEMS["FISHING_SHIP"][0]) == 1
    uuid, = train.tick(g, train.TRAIN_TIMES["FISHING_SHIP"])
    return uuid


def test_the_dock_menu_has_the_fishing_ship_with_its_values():
    server, g = dock_map()
    eye, d = (12.5, 65.62, 12.5), gather.direction(-90, 40)           # look east and down at the dock
    assert g.map.pick_ground(eye, d) is None and train.open_menu(g, "Steve", fleet.pick(g, eye, d)) == DOCK
    (slot, icon, label), cost, t = train.ITEMS["FISHING_SHIP"], train.COSTS["FISHING_SHIP"], train.TRAIN_TIMES["FISHING_SHIP"]
    assert f"{slot}:{icon}:{label}:{cost['wood']} wood · {t} s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, slot) == 1 and g.stock["wood"] == 200 - cost["wood"]
    assert train.tick(g, t - 1) == []


def test_a_trained_ship_floats_on_the_water_in_front_of_the_dock():
    server, g = dock_map()
    uuid = trained(server, g)
    summon, = [c.split() for c in server.log if c.startswith("summon minecraft:oak_boat ")]
    assert summon[2:5] == ["15.5", "63.0", "14.5"]                    # the middle of the south side, on the surface
    assert g.map.wet(15, 14) and g.soldiers[uuid] == "FISHING_SHIP" and g.ships[uuid].cell == (15, 14)
    assert uuid not in g.villagers


def test_a_ship_sails_on_the_water_to_the_goal_and_stops():
    server, g = dock_map()
    uuid = trained(server, g)
    assert fleet.order(g, {uuid}, (21, 3)) == {uuid: (21, 3)}
    path = list(g.ships[uuid].path)
    assert path[-1] == (21, 3) and all(g.map.wet(*c) for c in path)  # never on the land, not through the dock
    steps = len(server.log)
    fleet.tick(g, 1.0)                                                 # 1.26 tiles per AoE2 second (wiki)
    assert len(server.log) - steps == 1
    for _ in range(40):
        fleet.tick(g, 1.0)
    assert g.ships[uuid].cell == (21, 3) and not g.ships[uuid].path
    tps = [c for c in server.log if c.startswith(f"execute as {uuid} at @s run tp @s ")]
    assert len(tps) == len(path) and all(g.map.wet(math.floor(float(c.split()[8])), math.floor(float(c.split()[10])))
                                         for c in tps)


def test_a_click_on_the_land_sends_the_ship_to_the_water_next_to_it():
    server, g = dock_map()
    uuid = trained(server, g)
    goal = fleet.order(g, {uuid}, (12, 5))[uuid]
    assert g.map.wet(*goal) and goal == (14, 5)                         # the nearest water cell
    assert fleet.order(g, {uuid}, (3, 5)) == {uuid: (14, 5)}          # far from the water: the nearest water (#1515)


def test_the_look_at_the_water_picks_the_water_cell_and_the_selection_sails_there():
    server, g = dock_map()
    uuid = trained(server, g)
    eye, d = (12.5, 65.62, 12.5), gather.direction(-60, 30)           # look east and down at the water
    assert g.map.pick_ground(eye, d) is None and (cell := fleet.pick(g, eye, d)) and g.map.wet(*cell)
    g.select(uuid)
    assert g.walk_to("Steve", cell) == {uuid: cell}
    assert not any(c.startswith("aoe moveto") for c in server.log)    # no Minecraft path finding for a boat


@pytest.mark.mc
def test_a_fishing_ship_and_its_crew_sail_to_the_goal_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool in the air: water at x, z 2..21
    rows = [[y + 1] * 24 for _ in range(24)]
    for z in range(2, 22):
        rows[z][2:22] = ["-"] * 20
    m = gather.Map(grid(rows))
    with run.Game(world) as game:
        game.command("forceload add -2 -2 26 26")
        game.command(f"fill 0 {y - 1} 0 23 {y} 23 stone_bricks")
        game.command(f"fill 2 {y} 2 21 {y} 21 water")
        assert "Summoned" in summon(game, "FISHING_SHIP", 3.5, y + 0.5, 3.5, "s")
        uuid = game.command("data get entity @e[type=oak_boat,tag=s,limit=1] UUID")
        ints = [int(i) for i in re.findall(r"-?\d+", uuid.rsplit(":", 1)[-1])]
        h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
        uuid = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
        g = types.SimpleNamespace(map=m, command=game.command, soldiers={uuid: "FISHING_SHIP"},   # fleet.tick reads
                                  ships={uuid: gather.Villager(uuid, (3.5, y, 3.5))}, data={}, player=1)  # the civ (#1687)
        assert fleet.order(g, {uuid}, (18, 15)) == {uuid: (18, 15)}
        for _ in range(60):
            fleet.tick(g, 0.5)
            time.sleep(0.05)
        time.sleep(1.0)
        pos = [float(v) for v in re.findall(r"-?\d+\.\d+", game.command(f"data get entity {uuid} Pos"))]
        assert math.dist((pos[0], pos[2]), (18.5, 15.5)) < 0.5 and y - 0.5 < pos[1] < y + 1.5, pos   # it floats there
        assert "Test passed" in game.command(f"execute as {uuid} on passengers if entity @s[type=villager]")   # the crew
