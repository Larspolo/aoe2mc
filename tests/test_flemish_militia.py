"""Flemish Militia (#2155): the barracks of the Burgundians trains the Flemish Militia from the Feudal Age, faster from
the Castle Age (the key "faster"). The Castle and the Imperial Age give it more hit points and attack (the key "effect"
of CASTLE_AGE and IMPERIAL_AGE)."""
from test_castle_upgrades import setup

import units
from game import combat, replay, train

FEUDAL, CASTLE, IMPERIAL = ("FEUDAL_AGE",), ("FEUDAL_AGE", "CASTLE_AGE"), ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
NAME = "FLEMISH_MILITIA"


def barracks(civ="BURGUNDIANS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["fm"] = NAME
    return server, g


def test_the_unit_has_its_data():
    assert NAME in replay.SPEEDS and len(train.HELP[NAME]) <= 50
    assert units.classify(NAME)["id"] == "minecraft:zombie_villager"


def test_the_train_time_is_shorter_from_the_castle_age():
    fast = train.BY_KEY["faster"][NAME][1]
    assert [train.seconds(barracks(ages=a)[1], NAME) for a in (FEUDAL, CASTLE, IMPERIAL)] == [train.TRAIN_TIMES[NAME], fast, fast]


def test_each_age_gives_more_values():
    feudal, castle, imperial = (train.stats(barracks(ages=a)[1], NAME) for a in (FEUDAL, CASTLE, IMPERIAL))
    assert feudal.hp < castle.hp < imperial.hp and feudal.attack < castle.attack < imperial.attack
    eagle = train.stats(barracks(ages=CASTLE)[1], "EAGLE_SCOUT")                    # the first effect of CASTLE_AGE
    assert eagle.attack > combat.stats("EAGLE_SCOUT").attack


def test_the_age_up_gives_the_live_militia_the_new_values():
    server, g = barracks(ages=CASTLE)
    hp = train.stats(g, NAME).hp
    train.research(g, {"name": "IMPERIAL_AGE"})
    assert combat.stats_command("fm", NAME, train.stats(g, NAME)) in server.log
    assert train.stats(g, NAME).hp > hp

