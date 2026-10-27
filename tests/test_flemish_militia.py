"""Flemish Militia (#2155): the barracks of the Burgundians trains the Flemish Militia from the Feudal Age (slot 25: 35 food,
25 gold, 16 s; 14 s from the Castle Age), with the values of the AoE2 DE wiki infobox "Flemish Militia" (revision
1090747). The Castle and the Imperial Age give it more hit points, attack and bonus (the key "effect" of CASTLE_AGE and
IMPERIAL_AGE): 40, 55 and 60 hit points. Only the Burgundians have it."""
from test_castle_upgrades import BARRACKS, setup
from test_forging import menus

import units
from game import build, civs, combat, replay, train

FEUDAL, CASTLE, IMPERIAL = ("FEUDAL_AGE",), ("FEUDAL_AGE", "CASTLE_AGE"), ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
NAME = "FLEMISH_MILITIA"


def barracks(civ="BURGUNDIANS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["fm"] = NAME
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert build.AGE[NAME] == 1                    # the cost and time: the menu line (#2182)
    assert combat.stats(NAME) == (40, 5, 1, 1, 0, 2.0, {"camel": 4, "cavalry": 6, "elephant": 6, "ship": 4},
                                  ("infantry", "unique"))
    assert replay.SPEEDS[NAME] == 0.94 and combat.sight(NAME) == 7 and len(train.HELP[NAME]) <= 50
    assert units.classify(NAME)["id"] == "minecraft:zombie_villager"


def test_the_train_time_is_shorter_from_the_castle_age():
    assert [train.seconds(barracks(ages=a)[1], NAME) for a in (FEUDAL, CASTLE, IMPERIAL)] == [16, 14, 14]
    assert train.seconds(barracks(ages=CASTLE)[1], "EAGLE_SCOUT") == 35            # the other FASTER unit (#1555)


def test_each_age_gives_the_wiki_values():
    want = {FEUDAL: (40, 5, {"camel": 4, "cavalry": 6, "elephant": 6, "ship": 4}),
            CASTLE: (55, 8, {"camel": 5, "cavalry": 7, "elephant": 6, "ship": 5}),
            IMPERIAL: (60, 11, {"camel": 6, "cavalry": 8, "elephant": 6, "ship": 6})}
    for ages, (hp, attack, bonus) in want.items():
        s = train.stats(barracks(ages=ages)[1], NAME)
        assert (s.hp, s.attack, s.bonus, s.melee, s.pierce) == (hp, attack, bonus, 1, 1), ages
    eagle = train.stats(barracks(ages=CASTLE)[1], "EAGLE_SCOUT")                    # the first effect of CASTLE_AGE
    assert eagle.attack == combat.stats("EAGLE_SCOUT").attack + 3


def test_the_age_up_gives_the_live_militia_the_new_values():
    server, g = barracks(ages=CASTLE)
    train.research(g, {"name": "IMPERIAL_AGE"})
    assert combat.stats_command("fm", NAME, train.stats(g, NAME)) in server.log
    assert train.stats(g, NAME).hp == 60


def test_only_the_burgundians_have_it():
    assert set(civs.MISSING[NAME]) == {r["name"] for r in civs.ROWS} - {"BURGUNDIANS"}
    server, g = barracks(ages=FEUDAL)
    train.open_menu(g, "Steve", BARRACKS)
    assert " 25:zombie_villager_spawn_egg:Flemish Militia:35 food · 25 gold · 16 s · queue 0/15" in menus(server)[-1]
    server, g = barracks(ages=())
    train.open_menu(g, "Steve", BARRACKS)
    assert " 25:gray_dye:Flemish Militia:35 food · 25 gold · 16 s · Needs the Feudal Age" in menus(server)[-1]
    for civ in ("BRITONS", "FRANKS"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Flemish Militia" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", BARRACKS, NAME) is None, civ
