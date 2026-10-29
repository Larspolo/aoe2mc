"""Savar (#2014): the Persians upgrade the cavalier to the savar at the stable in the Imperial Age, in place of the
paladin and in the slot of Cavalier (the AoE2 DE wiki page "Savar"). Then the live cavaliers are savars and the stable
trains the savar. The other civilizations do not see it."""
import re

from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
CIVS = sorted(set().union(*civs.MISSING.values()))
OWN = next(c for c in CIVS if c not in civs.MISSING["SAVAR_UPGRADE"])   # a civilization of the savar (the data)
OTHER = next(c for c in CIVS if c in civs.MISSING["SAVAR_UPGRADE"] and c not in civs.MISSING["PALADIN_UPGRADE"])


def item(menu, name, kind):
    """True when the menu has the item `name` that ends with `kind` ("queue" or "research")."""
    return re.search(rf" \d+:\w+:{name}:[^:]* {kind}", " " + menu) is not None


def cavaliers(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["kn"] = "KNIGHT"
    g.game.entities.setdefault("kn", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    research(g, STABLE, "CAVALIER_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    return server, g


def test_the_savar_civilization_sees_savar_in_place_of_paladin():
    server, _ = cavaliers(OWN)
    menu = menus(server)[-1] + " "
    assert item(menu, "Savar", "research") and "Paladin" not in menu


def test_another_civilization_sees_paladin_and_not_savar():
    server, _ = cavaliers(OTHER)
    menu = menus(server)[-1] + " "
    assert item(menu, "Paladin", "research") and "Savar" not in menu


def test_the_live_cavaliers_become_savars_and_the_stable_trains_them():
    server, g = cavaliers(OWN)
    assert g.soldiers["kn"] == "CAVALIER"
    research(g, STABLE, "SAVAR_UPGRADE")
    assert g.soldiers["kn"] == "SAVAR"
    assert combat.stats_command("kn", "SAVAR") in server.log and combat.label_command("kn", "SAVAR") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert item(menu, "Savar", "queue") and ":Cavalier:" not in menu
    assert train.queue(g, "Steve", STABLE, "SAVAR") and train.queue(g, "Steve", STABLE, "CAVALIER") is None
