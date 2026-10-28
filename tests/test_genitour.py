"""Genitour (#1610): the archery range of the Berbers trains the genitour from the Castle Age (slot 19: 40 food,
35 wood, 25 s) and researches Elite Genitour in the Imperial Age (slot 20: 500 food, 450 wood, 60 s), with the values
of the AoE2 DE wiki infobox "Genitour (Age of Empires II)". The upgrade turns the live genitours into elite ones, and
the archery range then trains the elite genitour. The Berber cavalry bonus (15 % and 20 % cheaper in the Castle and
Imperial Age, civs.COSTS) also makes the genitour cheaper, as on the wiki."""
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def archery(civ="BERBERS", ages=IMPERIAL):
    server, g = setup(ages=ages, techs=())
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["ge"] = "GENITOUR"
    g.game.entities.setdefault("ge", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for unit in ("GENITOUR", "ELITE_GENITOUR", "ELITE_GENITOUR_UPGRADE"):
        assert len(train.HELP[unit]) <= 50
        assert "BERBERS" not in civs.MISSING[unit] and {"BRITONS", "FRANKS", "AZTECS"} <= set(civs.MISSING[unit])


def test_the_archery_range_has_the_genitour_from_the_castle_age_for_the_berbers():
    server, g = archery(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert ":gray_dye:Genitour:40 food · 35 wood · 25 s · Needs the Castle Age" in menus(server)[-1]
    server, g = archery(ages=CASTLE)
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert f" {train.MORE + 1}:skeleton_horse_spawn_egg:Genitour:34 food · 30 wood · 25 s · queue 0/15 " in menu   # cavalry -15 %
    assert "Elite Genitour" not in menu                                # the upgrade: the Imperial Age
    for civ in ("BRITONS", "FRANKS"):
        server, g = archery(civ, IMPERIAL)
        train.open_menu(g, "Steve", RANGE)
        assert "Genitour" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = archery()
    train.open_menu(g, "Steve", RANGE)
    assert f" {train.MORE + 2}:book:Elite Genitour:500 food · 450 wood · 60 s · research " in menus(server)[-1] + " "
    research(g, RANGE, "ELITE_GENITOUR_UPGRADE")
    assert g.soldiers["ge"] == "ELITE_GENITOUR"
    assert combat.stats_command("ge", "ELITE_GENITOUR") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert f" {train.MORE + 1}:skeleton_horse_spawn_egg:Elite Genitour:32 food · 28 wood · 25 s · queue 0/15 " in menu   # -20 %
    assert ":Genitour:" not in menu and f"{train.MORE + 2}:book" not in menu
    assert train.queue(g, "Steve", RANGE, "ELITE_GENITOUR") and train.queue(g, "Steve", RANGE, "GENITOUR") is None
