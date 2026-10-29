"""Imperial Skirmisher (#1611): the Vietnamese upgrade the elite skirmisher to the imperial skirmisher at the archery
range in the Imperial Age, in the slot of Elite Skirmisher (the UUpCost and UUpTime of the AoE2 DE wiki infobox "Elite
Skirmisher (Age of Empires II)"). Then the live elite skirmishers are imperial skirmishers and the archery range trains
the imperial skirmisher. The other civilizations do not see it."""
from menu_line import item
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def imperial(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    research(g, RANGE, "ELITE_SKIRMISHER_UPGRADE")
    train.open_menu(g, "Steve", RANGE)
    return server, g


def test_the_vietnamese_see_it_after_elite_skirmisher():
    server, _ = imperial("VIETNAMESE")
    assert item(menus(server)[-1], "Imperial Skirmisher").endswith(" · research")


def test_other_civs_do_not_see_it():
    server, _ = imperial("BRITONS")
    assert "Imperial Skirmisher" not in menus(server)[-1]
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": "VIETNAMESE"}}
    train.open_menu(g, "Steve", RANGE)
    assert "Imperial Skirmisher" not in menus(server)[-1]                # not before Elite Skirmisher


def test_the_live_elite_skirmishers_become_imperial_skirmishers_and_the_range_trains_them():
    server, g = imperial("VIETNAMESE")
    assert g.soldiers["k"] == "ELITE_SKIRMISHER"
    research(g, RANGE, "IMPERIAL_SKIRMISHER_UPGRADE")
    assert g.soldiers["k"] == "IMPERIAL_SKIRMISHER"
    hp = train.stats(g, "IMPERIAL_SKIRMISHER")                        # the Vietnamese bonus: skirmishers more HP
    assert hp.hp > combat.stats("IMPERIAL_SKIRMISHER").hp and combat.stats_command("k", "IMPERIAL_SKIRMISHER", hp) in server.log
    assert combat.label_command("k", "IMPERIAL_SKIRMISHER") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert item(menu, "Imperial Skirmisher").endswith(" · queue 0/15")
    assert ":Elite Skirmisher:" not in menu
    assert train.queue(g, "Steve", RANGE, "IMPERIAL_SKIRMISHER")
    assert train.queue(g, "Steve", RANGE, "ELITE_SKIRMISHER") is None
