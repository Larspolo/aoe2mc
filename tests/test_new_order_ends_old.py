"""game/gather.py: a new order ends each old order of a unit, as in AoE2 (#3007): a walk into a building, a siege tower
or a transport ship, a conversion, a relic trip and a farm (Gather.new_order). Fake servers."""
from test_gather import FakeServer, grid
from test_garrison_game import Server, arrive
from test_monk_heal import HealServer

from game import combat, garrison, gather, monk, siege_tower, transport

TC = (2, 5, 2, 5)
TREE = (12, 9)
FARM = (16, 16)


def setup(villagers=2):
    """A flat 24 × 24 map (tile size 1): an own town center at blocks x 2-4, z 2-4 with free cells inside, a tree at
    TREE, a farm at FARM and villagers south of the town center."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5],
                "ref": 1, "inside": {"y": 65, "cells": [[3, 3], [2, 3], [4, 3]]}},
               {"kind": "other", "name": "TREE_OAK", "tile": [TREE[0] + 0.5, TREE[1] + 0.5]},
               {"kind": "building", "name": "FARM", "player": 1, "tile": [FARM[0] + 0.5, FARM[1] + 0.5],
                "footprint": [FARM[0] - 1, FARM[1] - 1, FARM[0] + 2, FARM[1] + 2]}]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [6.5 + k, 9.5]}
                for k in range(villagers)]
    server = Server({f"v{k}": {"Pos": (6.5 + k, 64.0, 9.5)} for k in range(villagers)})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), carry=3, chop=0.25, start={}).setup()
    g.paper = True
    server.targets = {combat.target_uuid(o["footprint"]) for o in objects if o["kind"] == "building"}
    return server, g


def test_a_villager_with_a_garrison_order_that_goes_to_chop_delivers_its_wood():
    server, g = setup()
    g.choose({"v0"}, "v0")
    assert garrison.order(g, "Steve", (3, 3)) == TC and g.entering == {"v0": TC}
    g.paper = False                                                    # the villager walks with its own path
    g.send(TREE)
    assert not g.entering and g.villagers["v0"].state == "to_tree"
    wood = g.stock["wood"]
    for _ in range(60):
        g.step()
    assert not g.garrisons.get(TC) and g.stock["wood"] > wood        # it drops its wood and stays out


def test_a_move_order_near_the_door_ends_the_garrison_order():
    server, g = setup()
    g.choose({"v0"}, "v0")
    garrison.order(g, "Steve", (3, 3))
    x, z = garrison.door(g, TC)
    g.walk_to("Steve", (x, z + 2))
    assert not g.entering
    arrive(server, g, TC)
    server.entities["v0"]["Pos"] = (x + 0.5, 64.0, z + 0.5)
    g.step()
    assert not g.garrisons.get(TC)


def test_a_farmer_with_a_garrison_order_frees_its_farm():
    server, g = setup()
    g.choose({"v0"}, "v0")
    g.send(FARM)
    assert g.farmers == {FARM: "v0"}
    garrison.order(g, "Steve", (3, 3))
    assert not g.farmers
    g.choose({"v1"}, "v1")
    g.send(FARM)
    assert g.farmers == {FARM: "v1"} and g.villagers["v1"].tree == FARM


def test_a_unit_with_a_siege_tower_order_that_attacks_does_not_ride_the_tower():
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [x, 4.5]}
               for u, n, p, x in [("tower", "SIEGE_TOWER", 1, 12.5), ("m", "MILITIA", 1, 4.5), ("foe", "MILITIA", 2, 20.5)]]
    server = FakeServer({o["uuid"]: {"Pos": (o["tile"][0], 64.0, 4.5)} for o in objects})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    g.paper = True
    g.choose({"m"}, "m")
    assert siege_tower.order(g, "Steve", "tower") and g.boarding == {"m": "tower"}
    g.attack("foe")
    assert not g.boarding
    server.entities["m"]["Pos"] = (12.5, 64.0, 5.5)                    # it passes the tower
    siege_tower.tick(g)
    assert not vars(g).get("towers", {}).get("tower")


def test_a_unit_with_a_transport_order_that_moves_does_not_board_the_ship():
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x, 5.5]}
               for u, n, x in [("ship", "TRANSPORT_SHIP", 15.5), ("m", "MILITIA", 10.5)]]
    server = FakeServer({"ship": {"Pos": (15.5, 63.0, 5.5)}, "m": {"Pos": (10.5, 64.0, 5.5)}})
    g = gather.Gather(server, grid([[64] * 14 + ["-"] * 10 for _ in range(24)], objects), start={}).setup()
    g.paper = True
    g.choose({"m"}, "m")
    assert transport.order(g, "Steve", "ship") and set(g.loading) == {"m"}
    g.walk_to("Steve", (12, 5))
    assert not g.loading
    server.entities["m"]["Pos"] = (13.5, 64.0, 5.5)                    # it passes the boarding cell
    transport.tick(g)
    assert not vars(g).get("cargo", {}).get("ship")


def monks(*others):
    """A flat 40 × 40 map (tile size 1) with own monks "monk" at (5.5, 5.5) and "b" at (6.5, 5.5), a relic at block
    (10, 5), and others: (uuid, name, player, x, health, max)."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": u, "tile": [x, 5.5]} for u, x in [("monk", 5.5), ("b", 6.5)]]
    objects.append({"kind": "other", "name": "RELIC", "player": 0, "tile": [10.5, 5.5]})
    ents = {u: {"Pos": (x, 64.0, 5.5), "Health": 30.0, "Max": 30.0} for u, x in [("monk", 5.5), ("b", 6.5)]}
    for uuid, name, player, x, hp, top in others:
        objects.append({"kind": "unit", "name": name, "player": player, "uuid": uuid, "tile": [x, 5.5]})
        ents[uuid] = {"Pos": (x, 64.0, 5.5), "Health": hp, "Max": top}
    server = HealServer(ents)
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.paper = True
    return server, g


def test_a_monk_with_a_conversion_order_that_moves_stops_converting_and_heals_again():
    server, g = monks(("foe", "MILITIA", 2, 30.5, 40.0, 40.0), ("own", "MILITIA", 1, 7.5, 10.0, 40.0))
    g.choose({"monk"}, "monk")
    assert monk.convert_order(g, {"monk"}, "foe")
    g.walk_to("Steve", (5, 8))
    assert not g.converting
    server.log.clear()
    for _ in range(10):
        monk.convert(g, 0.25)
    assert not [c for c in server.log if c.startswith(("aoe moveto monk 30.5", "aoe stop monk"))]
    for _ in range(5):
        monk.heal(g, monk.EVERY)
    assert server.entities["own"]["Health"] > 10.0


def test_a_monk_with_a_relic_order_that_moves_frees_the_relic():
    server, g = monks()
    g.choose({"monk"}, "monk")
    assert monk.order(g, "Steve", (10, 5)) and g.fetching == {"monk": ("relic", 0)}
    g.walk_to("Steve", (5, 8))
    assert not g.fetching
    g.choose({"b"}, "b")
    assert monk.order(g, "Steve", (10, 5)) and g.fetching == {"b": ("relic", 0)}


def test_a_click_on_an_enemy_gives_the_monks_the_conversion_and_the_soldiers_the_attack():
    server, g = monks(("foe", "MILITIA", 2, 12.5, 40.0, 40.0), ("own", "MILITIA", 1, 7.5, 40.0, 40.0))
    g.choose({"monk", "own"}, "monk")
    g.target = lambda eye, d, pos: ("enemy", "foe", None)
    g.look = lambda name: ((5.5, 65.62, 5.5), (1.0, 0.0, 0.0))
    g.click("Steve")
    assert g.converting == {"monk": ["foe", 0.0, 0]}
    assert "aoe attack own foe" in server.log and not any(c.startswith("aoe attack monk") for c in server.log)
