"""game/train.py: the stable researches Husbandry in the Castle Age (150 food, 40 s, AoE2 DE wiki): the live and the
new mounted units of the player (cavalry, camels, elephants) walk 10 % faster (#1416)."""
import pytest
from test_bloodlines import menus, setup

from game import ai, civs, gather, train


def castle(civ=None):
    server, g = setup()
    g.techs.add("CASTLE_AGE")
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_cost_time_age_and_slot_are_those_of_aoe2():
    assert "HUSBANDRY" in train.TRAINS["STABLE"] and train.HELP["HUSBANDRY"]
    server, g = setup()                                                # the Feudal Age: not yet
    train.open_menu(g, "Steve", (11, 3))
    assert ":book:Husbandry:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), "HUSBANDRY") is None


def test_the_civilizations_without_husbandry_do_not_see_it():
    for civ in ("TEUTONS", "VIKINGS", "AZTECS", "CUMANS"):
        server, g = castle(civ)
        train.open_menu(g, "Steve", (11, 3))
        assert ":book:Husbandry:" not in menus(server)[-1], civ
    assert set(civs.MISSING["HUSBANDRY"]) >= {"INCAS", "MAYANS", "MAPUCHE", "MUISCA", "TUPI"}


def test_husbandry_makes_the_live_and_the_new_mounted_units_walk_10_percent_faster():
    server, g = castle()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert " 4:book:Husbandry:150 food · 40 s · research " in menus(server)[-1] + " "
    assert train.order(g, "Steve", rect, train.ITEMS["HUSBANDRY"][0]) == 1 and g.stock["food"] == 0
    train.tick(g, 40)
    assert "HUSBANDRY" in g.techs
    assert ai.speed_command("s", "SCOUT_CAVALRY", g.map.T, gather.NORMAL * 1.1) in server.log   # the live scout
    assert not any(c.startswith("aoe speed m ") for c in server.log)  # not the militia
    for name in ("SCOUT_CAVALRY", "KNIGHT", "CAVALRY_ARCHER", "CAMEL_RIDER", "BATTLE_ELEPHANT"):
        assert train.speed(g, name) == pytest.approx(1.1), name     # also the new units: train.speed
    for name in ("MILITIA", "ARCHER", "VILLAGER_MALE", "MONK", "TRADE_CART"):
        assert train.speed(g, name) == 1, name
