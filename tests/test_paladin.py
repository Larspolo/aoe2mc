"""Cavalier and Paladin (#1501): the stable researches Cavalier in the Imperial Age (300 food, 300 gold, 80 s: the
UpCost and UpTime of the AoE2 DE wiki infobox "Knight"), then Paladin after it and in its slot (1300 food, 750 gold,
170 s: "Cavalier"). Each turns the live knight line into the next unit, and the stable trains it in the slot of the
knight (60 food, 75 gold, 30 s). Only the civilizations with the unit in the wiki chart see the upgrade."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def stable(civ="BYZANTINES", ages=IMPERIAL):   # no cavalry bonus
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["kn"] = "KNIGHT"
    g.game.entities.setdefault("kn", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["after"]["PALADIN_UPGRADE"] == "CAVALIER_UPGRADE" and "CAVALIER_UPGRADE" not in train.BY_KEY["after"]
    for unit in ("CAVALIER", "PALADIN"):
        assert len(train.HELP[unit + "_UPGRADE"]) <= 50
    assert {"DANES", "SARACENS", "AZTECS"} <= set(civs.MISSING["CAVALIER_UPGRADE"])
    assert not {"FRANKS", "BRITONS", "PERSIANS"} & set(civs.MISSING["CAVALIER_UPGRADE"])
    assert {"BRITONS", "PERSIANS", "BULGARIANS"} <= set(civs.MISSING["PALADIN_UPGRADE"])
    assert not {"FRANKS", "TEUTONS", "BYZANTINES", "CELTS", "BURGUNDIANS"} & set(civs.MISSING["PALADIN_UPGRADE"])


def test_cavalier_is_in_the_stable_menu_in_the_imperial_age_and_paladin_after_it():
    server, g = stable(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", STABLE)
    assert "Cavalier" not in menus(server)[-1]                         # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 5:book:Cavalier:300 food · 300 gold · 80 s · research " in menu and "Paladin" not in menu
    research(g, STABLE, "CAVALIER_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    assert " 5:book:Paladin:1300 food · 750 gold · 170 s · research " in menus(server)[-1] + " "


def test_the_live_knights_become_cavaliers_then_paladins_and_the_stable_trains_them():
    server, g = stable()
    research(g, STABLE, "CAVALIER_UPGRADE")
    assert g.soldiers["kn"] == "CAVALIER"
    assert combat.stats_command("kn", "CAVALIER") in server.log and combat.label_command("kn", "CAVALIER") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert "3:horse_spawn_egg:Cavalier:60 food · 75 gold · 30 s · queue" in menu and ":Knight:" not in menu
    assert train.queue(g, "Steve", STABLE, "KNIGHT") is None           # the queue stays free for the research
    research(g, STABLE, "PALADIN_UPGRADE")
    assert g.soldiers["kn"] == "PALADIN" and combat.stats_command("kn", "PALADIN") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert "3:horse_spawn_egg:Paladin:60 food · 75 gold · 30 s · queue" in menu and ":Cavalier:" not in menu
    assert train.queue(g, "Steve", STABLE, "PALADIN") and train.queue(g, "Steve", STABLE, "CAVALIER") is None


def test_a_civilization_without_the_paladin_gets_only_the_cavalier():
    server, g = stable("BRITONS")
    train.open_menu(g, "Steve", STABLE)
    assert "5:book:Cavalier:" in menus(server)[-1]
    research(g, STABLE, "CAVALIER_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    assert "Paladin" not in menus(server)[-1]
    server, g = stable("SARACENS")
    train.open_menu(g, "Steve", STABLE)
    assert "Cavalier" not in menus(server)[-1] and ":Knight:" in menus(server)[-1]
