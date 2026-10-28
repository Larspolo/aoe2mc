"""game/train.py and game/gather.py: the mill researches Crop Rotation in the Imperial Age after Heavy Plow (250 food and
250 wood, 70 AoE2 seconds: AoE2 DE wiki). After the research the live and the new farms of the player have 175 more
food, and a villager carries no more food (#1578)."""
from test_horse_collar import menus, setup

from game import civs, gather, train


def imperial(food=250, wood=250):
    server, g = setup(food, wood)
    g.techs |= {"CASTLE_AGE", "IMPERIAL_AGE", "HORSE_COLLAR", "HEAVY_PLOW"}
    return server, g


def research(g):
    train.queue(g, "Steve", (3, 3), "CROP_ROTATION")
    train.tick(g, 69)
    assert "CROP_ROTATION" not in g.techs
    train.tick(g, 1)
    assert "CROP_ROTATION" in g.techs and not any(g.queues.values())


def test_the_mill_menu_has_crop_rotation_in_the_imperial_age_after_heavy_plow():
    server, g = imperial()
    g.techs -= {"IMPERIAL_AGE"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Crop Rotation" not in menus(server)[-1]                    # the Castle Age
    server, g = imperial()
    train.open_menu(g, "Steve", (3, 3))
    assert " 0:book:Crop Rotation:250 food · 250 wood · 70 s · research" in menus(server)[-1] + " "
    g.techs -= {"HEAVY_PLOW"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Crop Rotation" not in menus(server)[-1]                    # Heavy Plow first
    assert {"BRITONS", "KHITANS", "TURKS"} <= set(civs.MISSING["CROP_ROTATION"])
    assert "FRANKS" not in civs.MISSING["CROP_ROTATION"]


def test_live_and_new_farms_of_the_player_get_175_food():
    server, g = imperial()
    g.map.farms[(9, 9)] = 100
    farm = g.map.farm_food
    research(g)
    assert g.map.farms == {(9, 9): 275, (17, 17): gather.FARM_FOOD}   # not the farm of player 2
    g.map.building("FARM", (12, 15, 12, 15), (13, 13), True)
    assert g.map.farms[(13, 13)] == farm + 175


def test_a_villager_carries_no_more_food():
    server, g = imperial()
    before = {r: g.limit(r) for r in ("food", "wood", "gold", "stone")}
    research(g)
    assert {r: g.limit(r) for r in before} == before
