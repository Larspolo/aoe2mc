"""game/train.py: the stable researches Husbandry in the Castle Age (AoE2 DE wiki): the live and the new mounted units of
the player (cavalry, camels, elephants) walk faster (#1416)."""
import pytest
from menu_line import item
from test_bloodlines import menus, setup

from game import ai, civs, gather, train


def castle(civ=None):
    server, g = setup()
    g.stock["food"] = 10000
    g.techs.add("CASTLE_AGE")
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_not_in_the_feudal_age():
    server, g = setup()                                                # the Feudal Age: not yet
    train.open_menu(g, "Steve", (11, 3))
    assert ":book:Husbandry:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), "HUSBANDRY") is None


def test_the_civilizations_without_husbandry_do_not_see_it():
    for civ in sorted(civs.MISSING["HUSBANDRY"])[:4]:
        server, g = castle(civ)
        train.open_menu(g, "Steve", (11, 3))
        assert ":book:Husbandry:" not in menus(server)[-1], civ


def test_husbandry_makes_the_live_and_the_new_mounted_units_walk_faster():
    server, g = castle()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert item(menus(server)[-1], "Husbandry").endswith(" · research")
    food = g.stock["food"] - train.price(g, "HUSBANDRY").get("food", 0)
    assert train.order(g, "Steve", rect, train.ITEMS["HUSBANDRY"][0]) == 1 and g.stock["food"] == food
    train.tick(g, train.seconds(g, "HUSBANDRY", "STABLE"))
    assert "HUSBANDRY" in g.techs
    fast = train.speed(g, "SCOUT_CAVALRY")
    assert fast > 1 and ai.speed_command("s", "SCOUT_CAVALRY", g.map.T, gather.NORMAL * fast) in server.log   # the live scout
    assert not any(c.startswith("aoe speed m ") for c in server.log)  # not the militia
    for name in ("SCOUT_CAVALRY", "KNIGHT", "CAVALRY_ARCHER", "CAMEL_RIDER", "BATTLE_ELEPHANT"):
        assert train.speed(g, name) == pytest.approx(fast), name    # also the new units: train.speed
    for name in ("MILITIA", "ARCHER", "VILLAGER_MALE", "MONK", "TRADE_CART"):
        assert train.speed(g, name) == 1, name
