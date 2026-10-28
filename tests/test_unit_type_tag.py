"""A unit that a trigger or the game program makes has the type tag aoe2mc.t<AoE2 ID>, as a scenario unit (#2974):
the typed trigger conditions count it."""
import re

import numpy as np
from test_train_stable import setup
from test_trigger_objects import effect, lines

import aoe2mc
import units
from game import train


def flat(line):
    return re.sub(r"\s", "", line)


def test_create_object_gives_the_rider_the_type_tag():
    summon, = lines([effect(aoe2mc.CREATE_OBJECT, "KNIGHT", tile=(3, 5))])
    assert 'Tags:["aoe2mc.p1","aoe2mc.t38"]' in flat(summon)


def test_a_created_hero_is_its_hero_mob():
    hero = units.make_entity(dict(name="RICHARD_THE_LIONHEART", player=1, hero=True), {}, (0.0, 0.0, 0.0),
                             np.random.default_rng(1))
    summon, = lines([effect(aoe2mc.CREATE_OBJECT, "RICHARD_THE_LIONHEART", kind="H", tile=(3, 5))])
    assert summon.split()[1] == str(hero["id"]) != "minecraft:wolf" and "minecraft:zombie" in summon
    assert "aoe2mc.t160" in summon


def test_replace_and_garrisoned_objects_of_a_hero_are_its_hero_mob():
    e = dict(type=aoe2mc.REPLACE_OBJECT, message="", player=1, target=1, time=0, object=("U", "MILITIA"),
             object2=("H", "RICHARD_THE_LIONHEART"), tile=[-1, -1], area=[0, 0, 9, 9])
    summon = [x for x in lines([e]) if " summon " in x]
    assert summon and "minecraft:wolf" not in summon[0] and "minecraft:zombie" in summon[0] and "aoe2mc.t160" in summon[0]
    c = aoe2mc.Effect(dict(id=1), 4, None, {}, __import__("collections").Counter(), True, {}, {}, set(), {}, {}, [])
    aoe2mc.buildings.INSIDE[5] = ([(1, 1)], 70, (1, 1))
    try:
        g = dict(type=aoe2mc.CREATE_GARRISONED_OBJECT, player=1, object2=("H", "RICHARD_THE_LIONHEART"), selected=[5])
        summon, = aoe2mc.garrisoned_lines(g, c)
    finally:
        del aoe2mc.buildings.INSIDE[5]
    assert "minecraft:wolf" not in summon and "minecraft:zombie" in summon and "aoe2mc.t160" in summon


def test_a_trained_militia_has_the_type_tag():
    server, g = setup()
    train.summon(g, "MILITIA", (5.5, 64.0, 5.5))
    summon, = [c for c in server.log if c.startswith("summon")]
    assert '"aoe2mc.t74"' in flat(summon)


def test_the_id_of_the_scenario_wins():
    nbt = units.make_entity(dict(name="MILITIA", player=1, id=75), {}, (0.0, 0.0, 0.0), np.random.default_rng(1))
    assert [str(t) for t in units.top_entity(nbt)["Tags"]] == ["aoe2mc.p1", "aoe2mc.t75"]
