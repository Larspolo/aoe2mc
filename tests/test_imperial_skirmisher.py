"""Imperial Skirmisher (#1611): the Vietnamese upgrade the elite skirmisher to the imperial skirmisher at the archery
range in the Imperial Age, in the slot of Elite Skirmisher (300 wood, 300 gold, 50 s: the UUpCost and UUpTime of the AoE2
DE wiki infobox "Elite Skirmisher (Age of Empires II)"). Then the live elite skirmishers are imperial skirmishers and the
archery range trains the imperial skirmisher (25 food, 35 wood, 22 s). The other civilizations do not see it."""
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

from game import civs, combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def imperial(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    research(g, RANGE, "ELITE_SKIRMISHER_UPGRADE")
    train.open_menu(g, "Steve", RANGE)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["IMPERIAL_SKIRMISHER_UPGRADE"] == {"wood": 300, "gold": 300}
    assert train.TRAIN_TIMES["IMPERIAL_SKIRMISHER_UPGRADE"] == 50 and train.TECH_AGE["IMPERIAL_SKIRMISHER_UPGRADE"] == 3
    assert train.AFTER["IMPERIAL_SKIRMISHER_UPGRADE"] == "ELITE_SKIRMISHER_UPGRADE"
    assert train.COSTS["IMPERIAL_SKIRMISHER"] == {"food": 25, "wood": 35} and train.TRAIN_TIMES["IMPERIAL_SKIRMISHER"] == 22
    s = combat.stats("IMPERIAL_SKIRMISHER")
    assert (s.hp, s.attack, s.melee, s.pierce, s.range, s.reload) == (35, 4, 0, 5, 5, 3.0)
    assert s.bonus == {combat.ARC: 5, combat.SPE: 4} and combat.sight("IMPERIAL_SKIRMISHER") == 7
    assert len(train.HELP["IMPERIAL_SKIRMISHER_UPGRADE"]) <= 50
    assert "VIETNAMESE" not in civs.MISSING["IMPERIAL_SKIRMISHER_UPGRADE"]
    assert {"BRITONS", "CHINESE", "MAYANS"} <= set(civs.MISSING["IMPERIAL_SKIRMISHER_UPGRADE"])


def test_the_vietnamese_see_it_after_elite_skirmisher():
    server, _ = imperial("VIETNAMESE")
    assert " 3:book:Imperial Skirmisher:300 wood · 300 gold · 50 s · research " in " " + menus(server)[-1] + " "


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
    hp = combat.stats("IMPERIAL_SKIRMISHER")._replace(hp=42)            # the Vietnamese bonus: skirmishers +20 % HP
    assert combat.stats_command("k", "IMPERIAL_SKIRMISHER", hp) in server.log
    assert combat.label_command("k", "IMPERIAL_SKIRMISHER") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert "1:drowned_spawn_egg:Imperial Skirmisher:25 food · 35 wood · 22 s · queue" in menu
    assert ":Elite Skirmisher:" not in menu
    assert train.queue(g, "Steve", RANGE, "IMPERIAL_SKIRMISHER")
    assert train.queue(g, "Steve", RANGE, "ELITE_SKIRMISHER") is None
