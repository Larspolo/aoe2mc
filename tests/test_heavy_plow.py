"""game/train.py and game/gather.py: the mill researches Heavy Plow in the Castle Age after Horse Collar (125 food and
125 wood, 40 AoE2 seconds: AoE2 DE wiki). After the research the live and the new farms of the player have 125 more
food, and a villager carries 1 more food, not more wood (#1424)."""
from test_horse_collar import menus, setup

from game import civs, gather, train


def castle(food=125, wood=125):
    server, g = setup(food, wood)
    g.techs |= {"CASTLE_AGE", "HORSE_COLLAR"}
    return server, g


def research(g):
    train.queue(g, "Steve", (3, 3), "HEAVY_PLOW")
    train.tick(g, 39)
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
    assert " 0:book:Heavy Plow:125 food · 125 wood · 40 s · research" in menus(server)[-1] + " "
    g.techs -= {"HORSE_COLLAR"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Heavy Plow" not in menus(server)[-1]                       # Horse Collar first
    assert "KHITANS" in civs.MISSING["HEAVY_PLOW"]


def test_live_and_new_farms_of_the_player_get_125_food():
    server, g = castle()
    g.map.farms[(9, 9)] = 100
    farm = g.map.farm_food
    research(g)
    assert g.map.farms == {(9, 9): 225, (17, 17): gather.FARM_FOOD}   # not the farm of player 2
    g.map.building("FARM", (12, 15, 12, 15), (13, 13), True)
    assert g.map.farms[(13, 13)] == farm + 125


def test_a_villager_carries_1_more_food_only():
    server, g = castle()
    before = {r: g.limit(r) for r in ("food", "wood", "gold", "stone")}
    research(g)
    assert {r: g.limit(r) for r in before} == before | {"food": before["food"] + 1}
    g.techs.add("WHEELBARROW")
    assert g.limit("food") == before["food"] + 4 and g.limit("wood") == before["wood"] + 3
