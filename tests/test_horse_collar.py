"""game/train.py and game/gather.py: the mill menu has "Horse Collar" (a book). A click queues it once; after the
research the live and the new farms of the player have more food (#726)."""
from urllib.parse import unquote

from menu_line import item, labels, order
from test_gather import FakeServer, grid

from game import gather, train


def setup(food=1000, wood=1000, age=1):
    """A flat 24 × 24 map (tile size 1): a mill of player 1 at blocks x 2-3, z 2-3, an own farm, a farm of player 2
    and a villager."""
    objects = [{"kind": "building", "name": "MILL", "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "building", "name": "FARM", "player": 1, "tile": [9.0, 9.0], "footprint": [8, 8, 11, 11]},
               {"kind": "building", "name": "FARM", "player": 2, "tile": [17.0, 17.0], "footprint": [16, 16, 19, 19]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [5.5, 5.5]}]
    server = FakeServer({"v": {"Pos": (5.5, 64.0, 5.5)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.stock.update(food=food, wood=wood)
    g.techs.update({"FEUDAL_AGE"} if age else ())                   # a Feudal Age technology (the key "age", #1046)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def research(g):
    train.queue(g, "Steve", (3, 3), "HORSE_COLLAR")
    train.tick(g, train.seconds(g, "HORSE_COLLAR", "MILL") - 1)
    assert g.techs == {"FEUDAL_AGE"}
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "HORSE_COLLAR"} and not any(g.queues.values())


def test_the_mill_menu_has_horse_collar():
    server, g = setup()
    assert train.open_menu(g, "Steve", (2, 3)) == (2, 4, 2, 4)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Mill ") and labels(cmd) == order(g, "MILL")   # the full menu
    assert item(cmd, "Horse Collar").endswith(" · research")


def test_a_click_queues_horse_collar_once_and_takes_its_cost():
    server, g = setup(food=500, wood=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    cost, slot = train.price(g, "HORSE_COLLAR"), train.SLOTS["HORSE_COLLAR"]
    left = (500 - cost.get("food", 0), 500 - cost.get("wood", 0))
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and (g.stock["food"], g.stock["wood"]) == left
    assert train.order(g, "Steve", rect, slot) == 0 and (g.stock["food"], g.stock["wood"]) == left
    assert item(menus(server)[-1], "Horse Collar").endswith(" · researching")


def test_not_enough_resources():
    server, g = setup()
    g.stock["food"] = food = train.price(g, "HORSE_COLLAR")["food"] - 1
    assert train.queue(g, "Steve", (3, 3), "HORSE_COLLAR") is None and g.stock["food"] == food


def test_live_farms_of_the_player_get_more_food():
    server, g = setup()
    g.map.farms[(9, 9)] = 100                                          # a farm in use
    research(g)
    more = gather.FARM_TECHS["HORSE_COLLAR"]
    assert g.map.farms == {(9, 9): 100 + more, (17, 17): gather.FARM_FOOD}   # not the farm of player 2
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
    assert any("Horse Collar is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Horse Collar" not in menus(server)[-1]


def test_an_empty_farm_stays_empty():
    server, g = setup()
    g.map.farms[(9, 9)] = 0
    research(g)
    assert g.map.farms[(9, 9)] == 0


def test_a_new_farm_has_more_food_and_full_wheat():
    server, g = setup()
    research(g)
    g.map.building("FARM", (12, 15, 12, 15), (13, 13), True)
    full = gather.FARM_FOOD + gather.FARM_TECHS["HORSE_COLLAR"]
    assert g.map.farms[(13, 13)] == full and (13, 13) in g.map.own_farms
    g.map.farms[(13, 13)] = full - 1
    g.harvest((13, 13))                                                # one food less: still age 7, no command
    assert not [c for c in server.log if "wheat[age=" in c]
    g.map.farms[(13, 13)] = int(full * 0.8)                            # a fifth less: the next wheat age
    g.harvest((13, 13))
    assert any("wheat[age=6]" in c for c in server.log)
