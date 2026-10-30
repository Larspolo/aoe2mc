"""The datapack predicate files have the keys of Minecraft 26.3 (#3139): an old key stops the server at load."""
import glob
import json
import os

import mcvalid
import numpy as np
import test_trigger_damage
import test_trigger_object_hp_condition

import aoe2mc


def test_old_keys_give_an_error():
    assert mcvalid.predicate_error({"condition": "minecraft:random_chance", "chance": 0.5})
    old = {"type": "minecraft:entity_properties", "entity": "this", "predicate": {"vehicle": {"type": "minecraft:horse"}}}
    assert "vehicle" in mcvalid.predicate_error(old)
    inner = {"type": "minecraft:entity_properties", "entity": "this", "predicate": {"minecraft:vehicle": {"nbt": "{}"}}}
    assert "nbt" in mcvalid.predicate_error(inner)
    assert mcvalid.predicate_error({"type": "minecraft:random_chance", "chance": 0.5}) is None


def test_the_predicates_of_the_datapack_load(tiny_world):
    names = glob.glob(os.path.join(tiny_world[0], "datapacks", "aoe2mc", "data", "*", "predicate", "*.json"))
    assert names                                                       # the ambience predicates
    for name in names:
        with open(name) as f:
            assert mcvalid.predicate_error(json.load(f)) is None, name


def test_the_predicates_of_the_triggers_load():
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=[test_trigger_damage.effect(20)])
    files = {**test_trigger_object_hp_condition.files()[1],          # the rider predicate of "Object HP" and of damage
             **aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}})[1]}
    predicates = {k: v for k, v in files.items() if "/predicate/" in k}
    assert "data/aoe2mc/predicate/rider.json" in predicates
    for name, d in predicates.items():
        assert mcvalid.predicate_error(d) is None, name
