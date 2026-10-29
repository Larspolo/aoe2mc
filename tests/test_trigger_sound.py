"""Timer triggers play a vanilla sound for the trigger effect "Play Sound" (#2644)."""
import json
import os

import numpy as np

import aoe2mc


def effect(sound="Town Bell", tile=(-1, -1), player=1):
    return dict(type=aoe2mc.PLAY_SOUND, message="", player=player, time=0, object=None, tile=list(tile),
                area=[-1] * 4, sound=sound)


def lines(effects, T=4):
    trig = dict(id=7, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def vanilla(name):
    """The vanilla sound of the first SOUNDS part in the name (data/sounds.jsonl)."""
    return next(s for part, s in aoe2mc.SOUNDS if part in name.upper())


def test_the_sound_name_part_gives_the_vanilla_sound_at_each_player():
    assert lines([effect()]) == [f"execute as @a at @s run playsound minecraft:{vanilla('Town Bell')} master @s"]


def test_an_unknown_or_empty_sound_name_plays_the_default_sound():
    default = aoe2mc.SOUNDS[-1][1]                                     # the row with the name ""
    for name in ("xyz", ""):
        assert lines([effect(name)]) == [f"execute as @a at @s run playsound minecraft:{default} master @s"]


def test_a_target_tile_plays_the_sound_there_on_the_ground():
    assert lines([effect("battle_horn", tile=(3, 5))]) == [
        f"playsound minecraft:{vanilla('battle_horn')} master @a 14.5 70 22.5"]


def test_the_default_line_is_last_and_each_sound_has_the_vanilla_form():
    rows = [json.loads(s) for s in open(os.path.join(os.path.dirname(aoe2mc.__file__), "data", "sounds.jsonl"))]
    assert [r["name"] for r in rows].index("") == len(rows) - 1      # the first match wins: "" matches all
    assert all(r["sound"].islower() and " " not in r["sound"] and ":" not in r["sound"] for r in rows)
