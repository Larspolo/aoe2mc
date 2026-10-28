"""Armored Elephant (#2139): the siege workshop of the South Asian civilizations (Bengalis, Dravidians, Gurjaras,
Hindustanis) trains the armored elephant from the Castle Age (slot 0: 120 food, 95 gold, 36 s) in place of the
battering ram, and researches Siege Elephant in the Imperial Age (slot 3: 850 food, 60 s) in place of Capped Ram, with
the values of the AoE2 DE wiki infoboxes "Armored Elephant" and "Siege Elephant". The other civilizations keep the ram line."""
from test_forging import menus
from test_siege_upgrades import WORKSHOP, research, setup

import units
from game import civs, combat, train

SOUTH_ASIAN = {"BENGALIS", "DRAVIDIANS", "GURJARAS", "HINDUSTANIS"}
CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def workshop(civ="HINDUSTANIS", ages=CASTLE + ("IMPERIAL_AGE",)):
    server, g = setup(ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["e"] = "ARMORED_ELEPHANT"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for unit in ("ARMORED_ELEPHANT", "SIEGE_ELEPHANT"):
        assert len(train.HELP[unit]) <= 50
        assert units.classify(unit)["id"] == "minecraft:ravager"
        assert {"siege", "ram", "elephant"} <= set(combat.STATS[unit].classes)
    for unit in ("ARMORED_ELEPHANT", "SIEGE_ELEPHANT_UPGRADE"):
        assert set(civs.MISSING[unit]) == {r["name"] for r in civs.ROWS} - SOUTH_ASIAN
    for unit in ("BATTERING_RAM", "CAPPED_RAM_UPGRADE", "SIEGE_RAM_UPGRADE"):
        assert SOUTH_ASIAN <= set(civs.MISSING[unit])
        assert "FRANKS" not in civs.MISSING[unit]


def test_a_south_asian_workshop_trains_the_elephant_and_not_the_ram():
    server, g = workshop(ages=CASTLE)
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 0:ravager_spawn_egg:Armored Elephant:120 food · 95 gold · 36 s · queue 0/15 " in menu
    assert "Battering Ram" not in menu and "Siege Elephant" not in menu        # the upgrade: the Imperial Age
    assert train.queue(g, "Steve", WORKSHOP, "BATTERING_RAM") is None
    assert train.queue(g, "Steve", WORKSHOP, "ARMORED_ELEPHANT")
    server, g = workshop("FRANKS", CASTLE)
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1]
    assert ":Battering Ram:" in menu and "Armored Elephant" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "ARMORED_ELEPHANT") is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = workshop("BENGALIS")
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 3:book:Siege Elephant:850 food · 60 s · research " in menu and "Capped Ram" not in menu
    research(g, WORKSHOP, "SIEGE_ELEPHANT_UPGRADE")
    assert g.soldiers["e"] == "SIEGE_ELEPHANT" and g.soldiers["r"] == "BATTERING_RAM"
    assert combat.stats_command("e", "SIEGE_ELEPHANT", train.stats(g, "SIEGE_ELEPHANT"), 0.75) in server.log   # #2248
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 0:ravager_spawn_egg:Siege Elephant:120 food · 95 gold · 36 s · queue 0/15 " in menu
    assert "Armored Elephant" not in menu and "3:book" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "SIEGE_ELEPHANT")
