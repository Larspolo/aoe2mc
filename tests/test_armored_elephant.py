"""Armored Elephant (#2139): the siege workshop of the South Asian civilizations (Bengalis, Dravidians, Gurjaras,
Hindustanis) trains the armored elephant from the Castle Age in place of the battering ram, and researches Siege
Elephant in the Imperial Age in place of Capped Ram. The other civilizations keep the ram line."""
from menu_line import item
from test_forging import menus
from test_siege_upgrades import WORKSHOP, research, setup

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def workshop(civ="HINDUSTANIS", ages=CASTLE + ("IMPERIAL_AGE",)):
    server, g = setup(ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["e"] = "ARMORED_ELEPHANT"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def text(g, name, building):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return " · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_a_south_asian_workshop_trains_the_elephant_and_not_the_ram():
    server, g = workshop(ages=CASTLE)
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert item(menu, "Armored Elephant").endswith(":Armored Elephant:" + text(g, "ARMORED_ELEPHANT", "SIEGE_WORKSHOP") +
                                                   "queue 0/15")
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
    up = item(menu, "Siege Elephant")
    assert up.endswith(":Siege Elephant:" + text(g, "SIEGE_ELEPHANT_UPGRADE", "SIEGE_WORKSHOP") + "research")
    assert "Capped Ram" not in menu
    research(g, WORKSHOP, "SIEGE_ELEPHANT_UPGRADE")
    assert g.soldiers["e"] == "SIEGE_ELEPHANT" and g.soldiers["r"] == "BATTERING_RAM"
    assert combat.stats_command("e", "SIEGE_ELEPHANT", train.stats(g, "SIEGE_ELEPHANT"), 0.75) in server.log   # #2248
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert item(menu, "Siege Elephant").endswith(":Siege Elephant:" + text(g, "SIEGE_ELEPHANT", "SIEGE_WORKSHOP") +
                                                 "queue 0/15")
    assert "Armored Elephant" not in menu and up not in menu
    assert train.queue(g, "Steve", WORKSHOP, "SIEGE_ELEPHANT")
