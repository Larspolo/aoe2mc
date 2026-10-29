"""game/fleet.py: a fishing ship gathers a fish and brings the food to the nearest own dock (#1384). Fake server, no
Minecraft."""
import shutil
import time
import types

import pytest
from test_build_site import Server
from test_gather import grid

from game import fleet, gather, run, train

DOCK = (14, 17, 11, 14)                                                # block footprint (x0, x1, z0, z1)
SALMON = gather.FISH_FOOD["FISH_SALMON"]                               # the food of a salmon in the data


def fish_map(food=None):
    """The map of test_dock_train (land at x < 14, water at x >= 14, a dock of player 1 at the shore) with a salmon at
    tile (20, 12), a second salmon at (21, 14) and a shore fish at (14, 3)."""
    rows = [[64] * 14 + ["-"] * 10 for _ in range(24)]
    data = grid(rows, [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
                       {"kind": "building", "name": "DOCK", "player": 1, "tile": [15.5, 12.5], "footprint": [14, 11, 17, 14]},
                       {"kind": "other", "name": "FISH_SALMON", "tile": [20.5, 12.5]},
                       {"kind": "other", "name": "FISH_SALMON", "tile": [21.5, 14.5]},
                       {"kind": "other", "name": "SHORE_FISH", "tile": [14.5, 3.5]}])
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = Server({"Steve": {"Pos": (12.5, 64.0, 12.5), "Rotation": (-90.0, 40.0)}})
    g = gather.Gather(server, data).setup()
    g.stock["wood"] = 200
    if food is not None:
        g.map.fish[20, 12] = food
    rect = train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", rect, train.slots("DOCK", "FISHING_SHIP")[0]) == 1
    uuid, = train.tick(g, train.TRAIN_TIMES["FISHING_SHIP"])
    return server, g, uuid


def play(g, seconds, dt=0.25):
    for _ in range(round(seconds / dt)):
        fleet.tick(g, dt)


def test_the_map_knows_the_own_docks_and_the_fish_mobs():
    server, g, uuid = fish_map()
    assert g.map.docks == [{(x, z) for x in range(14, 17) for z in range(11, 14)}]
    assert g.map.fish_mobs == {(20, 12): "salmon", (21, 14): "salmon", (14, 3): "cod"}


def test_a_ship_gathers_at_the_aoe2_rate_and_carries_one_load():
    server, g, uuid = fish_map()
    v = g.ships[uuid]
    assert fleet.fish(g, {uuid}, (20, 12)) == {uuid}
    play(g, 10)                                                         # it sails there (about 4 tiles at 1.26 tiles/s)
    assert v.state == "chop" and v.cell in fleet.spots(g, (20, 12))
    load, food = v.load, g.map.fish[20, 12]
    play(g, 10)
    assert abs(v.load - load - 10 * fleet.rate(g, (20, 12))) <= 1 and food - g.map.fish[20, 12] == v.load - load
    assert any("entity.fishing_bobber.splash" in c for c in server.log)
    play(g, 30)
    assert v.load <= fleet.CARRY and g.map.fish[20, 12] == SALMON - fleet.CARRY - v.load * (v.state == "chop")


def test_a_ship_gathers_the_shore_fish_at_its_rate():
    server, g, uuid = fish_map()
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (14, 3))
    play(g, 30)
    assert v.state == "chop"
    load = v.load
    play(g, 25)
    assert abs(v.load - load - 25 * fleet.rate(g, (14, 3))) <= 1


def test_a_full_ship_drops_the_food_at_the_dock_and_sails_back():
    server, g, uuid = fish_map()
    v, food = g.ships[uuid], g.stock["food"]
    fleet.fish(g, {uuid}, (20, 12))
    for _ in range(400):
        fleet.tick(g, 0.25)
        if v.state == "to_drop":
            break
    assert v.load == fleet.CARRY and g.map.fish[20, 12] == SALMON - fleet.CARRY
    goal = v.path[-1]
    assert any(goal in g.map.around(c, water=True) for c in g.map.docks)
    for _ in range(60):
        fleet.tick(g, 0.25)
        if v.state != "to_drop":
            break
    assert g.stock["food"] == food + fleet.CARRY and v.load == 0 and v.tree == (20, 12) and v.state == "to_tree"
    assert f"scoreboard players add Food {g.board} {fleet.CARRY}" in server.log
    play(g, 10)
    assert v.state == "chop"


def test_an_empty_fish_is_removed_and_the_ship_takes_the_next_fish():
    server, g, uuid = fish_map(food=5)
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    play(g, 40)
    assert (20, 12) not in g.map.fish and (20, 12) not in g.map.fish_mobs
    kill = [c for c in server.log if c.startswith("kill @e[type=minecraft:salmon,x=20,")]
    assert kill and any("DeathLootTable" in c for c in server.log)  # no loot of a dead salmon
    play(g, 20)
    assert v.tree == (21, 14) and g.stock["food"] >= 5              # the 5 food at the dock, then the next fish


def test_a_move_order_stops_the_fishing():
    server, g, uuid = fish_map()
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    play(g, 20)
    load = v.load
    assert fleet.order(g, {uuid}, (21, 3)) == {uuid: (21, 3)}
    play(g, 30)
    assert v.state == "idle" and v.tree is None and v.load == load and v.cell == (21, 3)


def test_a_click_at_the_fish_sends_the_selected_ship():
    server, g, uuid = fish_map()
    g.select(uuid)
    eye = (12.5, 65.62, 12.5)
    d = next(gather.direction(-90, p / 2) for p in range(2, 80)
             if (c := fleet.pick(g, eye, gather.direction(-90, p / 2))) and c == (20, 12))
    assert fleet.fish_order(g, "Steve", eye, d)
    assert g.ships[uuid].tree == (20, 12) and g.ships[uuid].state == "to_tree"


@pytest.mark.mc
def test_an_empty_fish_leaves_no_mob_and_no_loot_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool in the air: water at x, z 0..7
    m = gather.Map(grid([["-"] * 8 for _ in range(8)], [{"kind": "other", "name": "FISH_SALMON", "tile": [1.5, 1.5]},
                                                        {"kind": "other", "name": "FISH_SALMON", "tile": [5.5, 5.5]}]))
    m.T = 4                                                            # tiles of 4 blocks: (1, 1) is x, z 4..7
    with run.Game(world) as game:
        game.command("forceload add -2 -2 26 26")
        game.command(f"fill 0 {y - 1} 0 23 {y - 1} 23 stone_bricks")
        game.command(f"fill 0 {y} 0 23 {y + 1} 23 water")
        for x in (6, 22):
            assert "Summoned" in game.command(f"summon minecraft:salmon {x} {y + 0.5} {x} {{NoAI:1b,PersistenceRequired:1b}}")
        g = types.SimpleNamespace(map=m, command=game.command)
        fleet.remove(g, (1, 1))
        time.sleep(1.5)
        assert game.command("execute if entity @e[type=salmon]") == "Test passed. Count: 1"
        assert game.command("execute if entity @e[type=item]") == "Test failed"         # no raw salmon
        assert game.command("execute if entity @e[type=salmon,x=22,y=200,z=22,distance=..2]").startswith("Test passed")
