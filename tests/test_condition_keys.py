"""#2832: the keys of each trigger condition (aoe2mc.CONDITION_KEYS) and the aoe2mc.json lists of the scenario mode
(aoe2mc.TRIGGER_LISTS) are one sorted line each, so that parallel trigger tickets do not conflict."""
import inspect
import json
import re

import numpy as np
import pytest

import aoe2mc
import scenarios


def table_lines(name):
    src = inspect.getsource(aoe2mc)
    body = src[src.index(f"\n{name} = {{"):]
    return re.findall(r'^    "?([A-Za-z_]+)"?: ', body[:body.index("\n}")], re.M)


@pytest.mark.parametrize("name", ["CONDITION_KEYS", "TRIGGER_LISTS"])
def test_the_lines_are_in_alphabetical_order(name):
    order = table_lines(name)
    assert order == sorted(order) and len(order) == len(getattr(aoe2mc, name))


def condition(**attrs):
    base = dict(quantity=3, source_player=2, target_player=3, unit_object=0, next_object=5, area_x1=1, area_y1=2,
                area_x2=4, area_y2=5, technology=22, variable=1, comparison=1, attribute=0, timer_id=2, object_list=74,
                object_group=0, object_type=0)
    return type("Condition", (), base | attrs)


def keys(kind, entities=frozenset({0}), techs=None):
    c = condition()
    return {k: v(c, entities, techs or {22: "LOOM"}) if callable(v) else getattr(c, v)
            for k, v in ((aoe2mc.OBJECT_KEYS if kind in aoe2mc.OBJECT_TESTS else {})
                         | aoe2mc.CONDITION_KEYS.get(kind, {})).items()}


def test_the_keys_of_the_conditions():
    assert keys(aoe2mc.DIPLOMACY_STATE) == {"player": 2, "target": 3, "diplomacy": 3}
    assert keys(aoe2mc.TECHNOLOGY_STATE) == {"player": 2, "technology": "LOOM", "quantity": 3}
    assert keys(aoe2mc.IN_AREA) == {"quantity": 3, "player": 2, "area": [1, 2, 4, 5], "object": 74, "group": 0, "class": 0}
    assert keys(aoe2mc.BRING_OBJECT_TO_OBJECT) == {"ref": 0, "unit": True, "player": 2, "next": 5, "next_unit": False}
    assert keys(aoe2mc.DESTROY_OBJECT, entities=frozenset()) == {"ref": 0, "unit": False, "player": 2}
    assert keys(aoe2mc.TIMER) == {}


def test_the_triggers_scenario_reads_as_before(tmp_path):
    texts = aoe2mc.read_scenario(scenarios.triggers(str(tmp_path / "t.aoe2scenario")))[4]
    area = next(c for t in texts["triggers"] for c in t["conditions"] if c["type"] == aoe2mc.IN_AREA)
    assert set(area) == {"type", "timer", "inverted", "quantity", "player", "area", "object", "group", "class"}


def test_write_objects_writes_each_list_that_is_not_empty(tmp_path):
    cols = aoe2mc.Columns(4, np.zeros((4, 4), np.int16), np.zeros((4, 4)), {0: "GRASS_1"}, 4, 2, np.random.default_rng(1))
    path = str(tmp_path / "a.json")
    aoe2mc.write_objects(path, 4, 4, 2, {}, [], cols, np.zeros((cols.n, cols.n), int),
                         lists={"research": [{"score": "#r1.0"}], "tech_states": []})
    data = json.load(open(path))
    assert data["research"] == [{"score": "#r1.0"}] and "tech_states" not in data
