"""Houfnice (#2143): the siege workshop of the Bohemians researches Houfnice in the Imperial Age (slot 22: 1100 food,
800 gold, 140 s; AoE2 DE wiki "Unique upgrade"), and their bombard cannons become houfnices (wiki infobox "Houfnice":
90 HP, 50 attack, +250 vs. buildings, +50 vs. heavy siege, 6 pierce armor, 0.7 blast). Other civilizations do not see it."""
from test_forging import menus
from test_siege_upgrades import WORKSHOP, research, setup

from game import build, civs, combat, train


def workshop(civ="BOHEMIANS"):
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.add("CHEMISTRY")
    g.soldiers["b"] = "BOMBARD_CANNON"
    g.game.entities.setdefault("b", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    # the cost and time of the upgrade: the menu line below (no copy of train.jsonl, #2182)
    assert build.AGE["HOUFNICE"] == build.AGE["BOMBARD_CANNON"] and build.NEEDS["HOUFNICE"] == "CHEMISTRY"
    assert train.COSTS["HOUFNICE"] == train.COSTS["BOMBARD_CANNON"] and len(train.HELP["HOUFNICE"]) <= 50
    s, b = combat.STATS["HOUFNICE"], combat.STATS["BOMBARD_CANNON"]
    assert (s.hp, s.attack, s.pierce, s.bonus["building"], s.bonus["heavysiege"]) == (90, 50, 6, 250, 50)
    assert s.classes == b.classes
    for name in ("HOUFNICE", "HOUFNICE_UPGRADE"):
        assert set(civs.MISSING[name]) == {r["name"] for r in civs.ROWS} - {"BOHEMIANS"}


def test_only_the_bohemians_see_the_upgrade():
    server, g = workshop("FRANKS")
    train.open_menu(g, "Steve", WORKSHOP)
    assert "Houfnice" not in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "HOUFNICE_UPGRADE") is None


def test_the_upgrade_changes_the_live_and_the_new_bombard_cannons():
    server, g = workshop()
    train.open_menu(g, "Steve", WORKSHOP)
    assert " 22:book:Houfnice:1100 food · 800 gold · 140 s · research " in menus(server)[-1] + " "
    research(g, WORKSHOP, "HOUFNICE_UPGRADE")
    assert g.soldiers["b"] == "HOUFNICE"
    assert combat.stats_command("b", "HOUFNICE", train.stats(g, "HOUFNICE")) in server.log
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 7:tnt_minecart:Houfnice:225 wood · 225 gold · 56 s · queue 0/15 " in menu
    assert "Bombard Cannon" not in menu and "22:book" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "HOUFNICE")


def test_no_upgrade_before_the_imperial_age():
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    g.data["players"] = {"1": {"civ": "BOHEMIANS"}}
    train.open_menu(g, "Steve", WORKSHOP)
    assert ":book:Houfnice:" not in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "HOUFNICE_UPGRADE") is None
