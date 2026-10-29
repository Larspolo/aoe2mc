"""Cavalier and Paladin (#1501): the stable researches Cavalier in the Imperial Age (the UpCost and UpTime of the AoE2
DE wiki infobox "Knight"), then Paladin after it and in its slot ("Cavalier"). Each turns the live knight line into the
next unit, and the stable trains it in the slot of the knight. Only the civilizations with the unit in the wiki chart
see the upgrade (civs.MISSING)."""
from menu_line import item
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
NO_CAVALIER, NO_PALADIN = set(train.civs.MISSING["CAVALIER_UPGRADE"]), set(train.civs.MISSING["PALADIN_UPGRADE"])


def stable(civ="BYZANTINES", ages=IMPERIAL):   # no cavalry bonus
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["kn"] = "KNIGHT"
    g.game.entities.setdefault("kn", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_cavalier_is_in_the_stable_menu_in_the_imperial_age_and_paladin_after_it():
    server, g = stable(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", STABLE)
    assert "Cavalier" not in menus(server)[-1]                         # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", STABLE)
    menu, slot = menus(server)[-1], train.SLOTS["CAVALIER_UPGRADE"]
    assert item(menu, "Cavalier").startswith(f"{slot}:") and item(menu, "Cavalier").endswith(" · research")
    assert "Paladin" not in menu
    research(g, STABLE, "CAVALIER_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    up = item(menus(server)[-1], "Paladin")
    assert up.startswith(f"{slot}:") and up.endswith(" · research")


def test_the_live_knights_become_cavaliers_then_paladins_and_the_stable_trains_them():
    server, g = stable()
    knight = f"{train.SLOTS['KNIGHT']}:"
    research(g, STABLE, "CAVALIER_UPGRADE")
    assert g.soldiers["kn"] == "CAVALIER"
    assert combat.stats_command("kn", "CAVALIER") in server.log and combat.label_command("kn", "CAVALIER") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert item(menu, "Cavalier").startswith(knight) and " · queue" in item(menu, "Cavalier") and ":Knight:" not in menu
    assert train.queue(g, "Steve", STABLE, "KNIGHT") is None           # the queue stays free for the research
    research(g, STABLE, "PALADIN_UPGRADE")
    assert g.soldiers["kn"] == "PALADIN" and combat.stats_command("kn", "PALADIN") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert item(menu, "Paladin").startswith(knight) and " · queue" in item(menu, "Paladin") and ":Cavalier:" not in menu
    assert train.queue(g, "Steve", STABLE, "PALADIN") and train.queue(g, "Steve", STABLE, "CAVALIER") is None


def test_a_civilization_without_the_paladin_gets_only_the_cavalier():
    server, g = stable(min(NO_PALADIN - NO_CAVALIER))
    train.open_menu(g, "Steve", STABLE)
    assert f"{train.SLOTS['CAVALIER_UPGRADE']}:book:Cavalier:" in menus(server)[-1]
    research(g, STABLE, "CAVALIER_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    assert "Paladin" not in menus(server)[-1]
    server, g = stable(min(NO_CAVALIER - set(train.civs.MISSING["KNIGHT"])))   # the knight, no upgrade
    train.open_menu(g, "Steve", STABLE)
    assert "Cavalier" not in menus(server)[-1] and ":Knight:" in menus(server)[-1]
