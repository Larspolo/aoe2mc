"""game/train.py and game/gather.py: the mill researches Heavy Plow in the Castle Age after Horse Collar (AoE2 DE wiki).
After the research the live and the new farms of the player have more food, and a villager carries more food, not more
wood (#1424)."""
from menu_line import item
from test_horse_collar import menus, setup

from game import gather, train


def castle(food=1000, wood=1000):
    server, g = setup(food, wood)
    g.techs |= {"CASTLE_AGE", "HORSE_COLLAR"}
    return server, g


def research(g):
    train.queue(g, "Steve", (3, 3), "HEAVY_PLOW")
    train.tick(g, train.seconds(g, "HEAVY_PLOW", "MILL") - 1)
    assert "HEAVY_PLOW" not in g.techs
    train.tick(g, 1)
    assert "HEAVY_PLOW" in g.techs and not any(g.queues.values())


def test_the_mill_menu_has_heavy_plow_in_the_castle_age_after_horse_collar():
    server, g = setup()
    g.techs |= {"HORSE_COLLAR"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Heavy Plow" not in menus(server)[-1]                       # the Feudal Age
    server, g = castle()
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Heavy Plow").endswith(" · research")
    g.techs -= {"HORSE_COLLAR"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Heavy Plow" not in menus(server)[-1]                       # Horse Collar first


def test_live_and_new_farms_of_the_player_get_more_food():
    server, g = castle()
    g.map.farms[(9, 9)] = 100
    farm, more = g.map.farm_food, gather.FARM_TECHS["HEAVY_PLOW"]
    research(g)
    assert g.map.farms == {(9, 9): 100 + more, (17, 17): gather.FARM_FOOD}   # not the farm of player 2
    g.map.building("FARM", (12, 15, 12, 15), (13, 13), True)
    assert g.map.farms[(13, 13)] == farm + more


def test_a_villager_carries_more_food_only():
    server, g = castle()
    before = {r: g.limit(r) for r in ("food", "wood", "gold", "stone")}
    research(g)
    assert {r: g.limit(r) for r in before} == before | {"food": before["food"] + gather.FOOD_CARRY["HEAVY_PLOW"]}
    plow = g.limit("food")
    g.techs.add("WHEELBARROW")
    assert g.limit("food") - plow == g.limit("wood") - before["wood"] > 0   # Wheelbarrow adds to both
