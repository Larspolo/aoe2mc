"""Xianbei Raider (#2160): the Wei archery range trains the Xianbei Raider from the Castle Age (slot 28: 65 wood, 35 gold,
29 s), with the values of the AoE2 DE wiki infobox "Xianbei Raider" (revision 1091372). It has no elite upgrade. Only the
Wei have it. The hit points are the base value: 36 and 40 come from the Wei bonus of each age."""
from test_castle_upgrades import RANGE, setup
from test_forging import menus

import units
from game import build, civs, combat, replay, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def archery_range(civ="WEI", ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert train.COSTS["XIANBEI_RAIDER"] == {"wood": 65, "gold": 35} and train.TRAIN_TIMES["XIANBEI_RAIDER"] == 29
    assert build.AGE["XIANBEI_RAIDER"] == 2 and len(train.HELP["XIANBEI_RAIDER"]) <= 50
    assert combat.stats("XIANBEI_RAIDER") == (30, 5, 0, 0, 4, 1.8, {"infantry": 1, "spearman": 3},
                                              ("archer", "cavalry", "unique"))
    assert combat.sight("XIANBEI_RAIDER") == 6 and replay.SPEEDS["XIANBEI_RAIDER"] == 1.4
    e = units.classify("XIANBEI_RAIDER")
    assert e["id"] == "minecraft:skeleton_horse"
    assert e["Passengers"][0]["equipment"]["mainhand"]["id"] == "minecraft:bow"


def test_only_the_wei_have_it():
    have = set().union(*civs.MISSING.values())
    assert have - set(civs.MISSING["XIANBEI_RAIDER"]) == {"WEI"}


def test_the_menu_has_the_unit_from_the_castle_age_for_the_wei():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert " 28:gray_dye:Xianbei Raider:65 wood · 35 gold · 29 s · Needs the Castle Age" in menus(server)[-1]
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    assert " 28:skeleton_horse_spawn_egg:Xianbei Raider:65 wood · 35 gold · 29 s · queue 0/15 " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", RANGE, "XIANBEI_RAIDER")
    for civ in ("BRITONS", "SHU"):
        server, g = archery_range(civ)
        train.open_menu(g, "Steve", RANGE)
        assert "Xianbei Raider" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", RANGE, "XIANBEI_RAIDER") is None, civ
