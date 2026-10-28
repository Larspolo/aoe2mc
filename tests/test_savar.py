"""Savar (#2014): the Persians upgrade the cavalier to the savar at the stable in the Imperial Age, in place of the
paladin and in the slot of Cavalier (1200 food, 600 gold, 160 s: the AoE2 DE wiki page "Savar"). Then the live
cavaliers are savars and the stable trains the savar (60 food, 75 gold, 30 s; 145 HP, 14 attack, 3/4 armor, +2 vs.
archers: the infobox). The other civilizations do not see it."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def cavaliers(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["kn"] = "KNIGHT"
    g.game.entities.setdefault("kn", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    research(g, STABLE, "CAVALIER_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["after"]["SAVAR_UPGRADE"] == "CAVALIER_UPGRADE"
    assert len(train.HELP["SAVAR_UPGRADE"]) <= 50
    assert "PERSIANS" in civs.MISSING["PALADIN_UPGRADE"] and "PERSIANS" not in civs.MISSING["SAVAR_UPGRADE"]
    assert {"FRANKS", "BRITONS", "TEUTONS"} <= set(civs.MISSING["SAVAR_UPGRADE"])


def test_the_persians_see_savar_in_place_of_paladin():
    server, _ = cavaliers("PERSIANS")
    menu = menus(server)[-1] + " "
    assert " 5:book:Savar:1200 food · 600 gold · 160 s · research " in menu and "Paladin" not in menu


def test_the_franks_see_paladin_and_not_savar():
    server, _ = cavaliers("FRANKS")
    menu = menus(server)[-1] + " "
    assert " 5:book:Paladin:" in menu and "Savar" not in menu


def test_the_live_cavaliers_become_savars_and_the_stable_trains_them():
    server, g = cavaliers("PERSIANS")
    assert g.soldiers["kn"] == "CAVALIER"
    research(g, STABLE, "SAVAR_UPGRADE")
    assert g.soldiers["kn"] == "SAVAR"
    assert combat.stats_command("kn", "SAVAR") in server.log and combat.label_command("kn", "SAVAR") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert "3:horse_spawn_egg:Savar:60 food · 75 gold · 30 s · queue" in menu and ":Cavalier:" not in menu
    assert train.queue(g, "Steve", STABLE, "SAVAR") and train.queue(g, "Steve", STABLE, "CAVALIER") is None
