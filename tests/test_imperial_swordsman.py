"""Two-Handed Swordsman and Champion (#1498): the barracks researches both upgrades in the Imperial Age, in the slot of
Long Swordsman, the champion after the two-handed swordsman (the UpCost and UpTime of the AoE2 DE wiki infoboxes "Long
Swordsman" and "Two-Handed Swordsman": 200 food, 100 gold, 45 s; 650 food, 350 gold, 70 s). Then the live long
swordsmen are two-handed swordsmen, then champions, and the barracks trains the new unit (50 food, 20 gold, 21 s)."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["TWO_HANDED_SWORDSMAN_UPGRADE"] == {"food": 200, "gold": 100}
    assert train.COSTS["CHAMPION_UPGRADE"] == {"food": 650, "gold": 350}
    assert (train.TRAIN_TIMES["TWO_HANDED_SWORDSMAN_UPGRADE"], train.TRAIN_TIMES["CHAMPION_UPGRADE"]) == (45, 70)
    assert train.TECH_AGE["TWO_HANDED_SWORDSMAN_UPGRADE"] == train.TECH_AGE["CHAMPION_UPGRADE"] == 3
    assert train.AFTER["TWO_HANDED_SWORDSMAN_UPGRADE"] == "LONG_SWORDSMAN_UPGRADE"
    assert train.AFTER["CHAMPION_UPGRADE"] == "TWO_HANDED_SWORDSMAN_UPGRADE"
    for n in ("TWO_HANDED_SWORDSMAN", "CHAMPION"):
        assert train.COSTS[n] == {"food": 50, "gold": 20} and train.TRAIN_TIMES[n] == 21
    assert (combat.stats("TWO_HANDED_SWORDSMAN").hp, combat.stats("CHAMPION").hp) == (65, 70)
    assert all(len(train.HELP[n]) <= 50 for n in ("TWO_HANDED_SWORDSMAN_UPGRADE", "CHAMPION_UPGRADE"))


def test_the_upgrades_are_in_the_slot_of_long_swordsman_in_the_imperial_age_in_order():
    server, g = setup()
    research(g, BARRACKS, "LONG_SWORDSMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Two-Handed" not in menus(server)[-1]                       # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert " 2:book:Two-Handed Swordsman:200 food · 100 gold · 45 s · research " in menu + " " and ":Champion:" not in menu
    research(g, BARRACKS, "TWO_HANDED_SWORDSMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert " 2:book:Champion:650 food · 350 gold · 70 s · research " in menus(server)[-1] + " "
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
        assert f"0:zombie_spawn_egg:{train.ITEMS[unit][2]}:50 food · 20 gold · 21 s · queue" in menu
        assert f":{old}:50 food" not in menu
    assert train.queue(g, "Steve", BARRACKS, "CHAMPION")
    assert train.queue(g, "Steve", BARRACKS, "TWO_HANDED_SWORDSMAN") is None
