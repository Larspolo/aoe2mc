"""Winged Hussar (#1558): the Poles and the Lithuanians upgrade the light cavalry to the winged hussar at the stable in
the Imperial Age, in place of the hussar upgrade and in the slot of Light Cavalry (600 food, 800 gold, 60 s: the
UpFromCost and UpFromTime of the AoE2 DE wiki infobox "Winged Hussar (Age of Empires II)"). Then the live light cavalry
are winged hussars and the stable trains the winged hussar (80 food, 30 s). The other civilizations do not see it."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def imperial(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    research(g, STABLE, "LIGHT_CAVALRY_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.AFTER["WINGED_HUSSAR_UPGRADE"] == "LIGHT_CAVALRY_UPGRADE"
    s = combat.stats("WINGED_HUSSAR")
    assert (s.hp, s.attack, s.melee, s.pierce, s.reload, s.bonus) == (80, 9, 1, 2, 1.9, {combat.GUN: 4})
    assert len(train.HELP["WINGED_HUSSAR_UPGRADE"]) <= 50
    assert {"POLES", "LITHUANIANS"} <= set(civs.MISSING["HUSSAR_UPGRADE"])
    assert not {"POLES", "LITHUANIANS"} & set(civs.MISSING["WINGED_HUSSAR_UPGRADE"])
    assert {"BRITONS", "HUNS", "MAGYARS", "TEUTONS"} <= set(civs.MISSING["WINGED_HUSSAR_UPGRADE"])


def test_the_poles_and_lithuanians_see_it_in_place_of_hussar():
    for civ in ("POLES", "LITHUANIANS"):
        server, _ = imperial(civ)
        menu = menus(server)[-1] + " "
        assert " 2:book:Winged Hussar:600 food · 800 gold · 60 s · research " in menu and ":Hussar:" not in menu


def test_other_civs_see_the_hussar_only():
    server, _ = imperial("MAGYARS")
    menu = menus(server)[-1]
    assert "Winged Hussar" not in menu and " 2:book:Hussar:" in " " + menu
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": "POLES"}}
    train.open_menu(g, "Steve", STABLE)
    assert "Winged Hussar" not in menus(server)[-1]                     # not before Light Cavalry


def test_the_live_light_cavalry_become_winged_hussars_and_the_stable_trains_them():
    server, g = imperial("POLES")
    assert g.soldiers["l"] == "LIGHT_CAVALRY"
    research(g, STABLE, "WINGED_HUSSAR_UPGRADE")
    assert g.soldiers["l"] == "WINGED_HUSSAR"
    assert combat.stats_command("l", "WINGED_HUSSAR") in server.log
    assert combat.label_command("l", "WINGED_HUSSAR") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert "0:horse_spawn_egg:Winged Hussar:80 food · 30 s · queue" in menu and ":Light Cavalry:" not in menu
    assert train.queue(g, "Steve", STABLE, "WINGED_HUSSAR")
    assert train.queue(g, "Steve", STABLE, "LIGHT_CAVALRY") is None
