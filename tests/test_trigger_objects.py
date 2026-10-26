"""Timer triggers create and remove objects in the converted world (#656)."""
import contextlib
import io
import os
from collections import Counter

import numpy as np

import aoe2mc
from tools import scenarios


def effect(type, name=None, kind="U", player=1, tile=(-1, -1), area=(-1, -1, -1, -1)):
    return dict(type=type, message="", player=player, time=0, object=(kind, name) if name else None,
                tile=list(tile), area=list(area))


def trig(effects, id=7):
    return dict(id=id, name="t", enabled=True, looping=False, conditions=[dict(type=aoe2mc.TIMER, timer=30,
                inverted=False)], effects=effects)


def lines(effects, stats=None, T=4):
    ground = np.full((64, 64), 70, np.int16)
    files = aoe2mc.trigger_files([trig(effects)], T, ground, {1: {"color": "blue"}}, stats)[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_create_object_summons_the_unit_with_the_player_tag():
    stats = Counter()
    summon, = lines([effect(aoe2mc.CREATE_OBJECT, "MILITIA", tile=(3, 5))], stats)
    assert summon.startswith("summon minecraft:zombie 14.5 70 22.5 {")   # the middle of tile (3, 5), on the ground
    assert 'Tags: ["aoe2mc.p1"]' in summon and "Pos" not in summon and stats == Counter(create=1)


def test_two_created_knights_have_no_fixed_uuid():
    a, b = lines([effect(aoe2mc.CREATE_OBJECT, "KNIGHT", tile=(3, 5)), effect(aoe2mc.CREATE_OBJECT, "KNIGHT", tile=(4, 5))])
    assert "UUID" not in a + b and "Passengers" in a                   # the rider stays on its horse


def test_create_object_of_a_building_is_not_supported_yet():
    stats = Counter()
    assert lines([effect(aoe2mc.CREATE_OBJECT, "MONASTERY", kind="B", tile=(3, 5))], stats) == []
    assert stats == Counter({"create (not supported yet)": 1})


def test_remove_object_kills_the_units_of_the_player_in_the_area():
    stats = Counter()
    kill, = lines([effect(aoe2mc.REMOVE_OBJECT, "ARCHER", player=2, area=(1, 2, 3, 2))], stats)
    assert kill == "kill @e[tag=aoe2mc.p2,type=minecraft:skeleton,x=4,y=-64,z=8,dx=11,dy=384,dz=3]"
    assert stats == Counter(remove=1)


def test_remove_object_of_a_rider_kills_its_mount_too():
    ride, kill = lines([effect(aoe2mc.REMOVE_OBJECT, "KNIGHT", area=(0, 0, 1, 1))])
    assert ride.startswith("execute as @e[tag=aoe2mc.p1,") and ride.endswith(" on vehicle run kill @s")
    assert kill == "kill " + ride.split(" ")[2]


def test_the_effect_tiles_turn_with_the_map():
    t = trig([effect(aoe2mc.CREATE_OBJECT, "MILITIA", tile=(3, 5)), effect(aoe2mc.REMOVE_OBJECT, area=(1, 2, 3, 2))])
    aoe2mc.turn_effects([t], 16, 1)                                     # one quarter turn: (x, y) -> (15 - y, x)
    assert t["effects"][0]["tile"] == [10, 3] and t["effects"][1]["area"] == [13, 1, 13, 3]
    assert t["effects"][1]["object"] is None                           # no type: all units of the player


def test_the_triggers_scenario_removes_the_archers(tmp_path):
    src = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "W"))
    ids = [t["id"] for t in aoe2mc.read_scenario(src)[4]["triggers"] if t["name"] == "Archer leaves"]
    path = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function", "trigger", f"{ids[0]}.mcfunction")
    with open(path) as f:
        assert f.read().startswith("kill @e[tag=aoe2mc.p2,type=minecraft:skeleton,x=0,y=-64,z=0,dx=95,")
    assert "timer triggers (chat, instructions, objects): 2, 1 remove" in out.getvalue()
