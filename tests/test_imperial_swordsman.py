"""Two-Handed Swordsman and Champion (#1498): the barracks researches both upgrades in the Imperial Age, in the slot of
Long Swordsman, the champion after the two-handed swordsman (the UpCost and UpTime of the AoE2 DE wiki infoboxes "Long
Swordsman" and "Two-Handed Swordsman"). Then the live long swordsmen are two-handed swordsmen, then champions, and the
barracks trains the new unit."""
from menu_line import item
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def test_the_upgrades_are_in_the_slot_of_long_swordsman_in_the_imperial_age_in_order():
    server, g = setup()
    research(g, BARRACKS, "LONG_SWORDSMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Two-Handed" not in menus(server)[-1]                       # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    two = item(menu, "Two-Handed Swordsman")
    assert two.split(":")[1] == "book" and two.endswith(" · research") and ":Champion:" not in menu
    research(g, BARRACKS, "TWO_HANDED_SWORDSMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    champion = item(menus(server)[-1], "Champion")
    assert champion.split(":")[0] == two.split(":")[0] and champion.endswith(" · research")   # the same slot
    server, g = setup(ages=IMPERIAL)
    train.open_menu(g, "Steve", BARRACKS)
    assert "Two-Handed" not in menus(server)[-1]                       # not before Long Swordsman


def test_the_live_long_swordsmen_become_two_handed_swordsmen_then_champions():
    server, g = setup(ages=IMPERIAL)
    research(g, BARRACKS, "LONG_SWORDSMAN_UPGRADE")
    assert g.soldiers["a"] == "LONG_SWORDSMAN"
    for tech, unit, old in (("TWO_HANDED_SWORDSMAN_UPGRADE", "TWO_HANDED_SWORDSMAN", "Long Swordsman"),
                            ("CHAMPION_UPGRADE", "CHAMPION", "Two-Handed Swordsman")):
        research(g, BARRACKS, tech)
        assert g.soldiers["a"] == unit
        assert combat.stats_command("a", unit) in server.log and combat.label_command("a", unit) in server.log
        train.open_menu(g, "Steve", BARRACKS)
        menu = menus(server)[-1]
        assert item(menu, train.ITEMS[unit][2]).endswith(" · queue 0/15")
        assert item(menu, old) is None
    assert train.queue(g, "Steve", BARRACKS, "CHAMPION")
    assert train.queue(g, "Steve", BARRACKS, "TWO_HANDED_SWORDSMAN") is None
