"""Timer triggers send their chat messages and instructions in the converted world (#648)."""
import os

import numpy as np

import aoe2mc
from tools import scenarios


def trig(id, conds, effects, enabled=True, looping=False):
    return dict(id=id, name=f"t{id}", enabled=enabled, looping=looping,
                conditions=[dict(type=t, timer=s, inverted=False) for t, s in conds],
                effects=[dict(type=t, message=m, player=1, time=d) for t, m, d in effects])


def read(root, name):
    with open(os.path.join(root, "datapacks", "aoe2mc", "data", "aoe2mc", "function", name)) as f:
        return f.read()


def test_scenario_triggers_are_read(tmp_path):
    texts = aoe2mc.read_scenario(scenarios.triggers(str(tmp_path / "t.aoe2scenario")))[4]
    welcome, knight, archer = texts["triggers"]
    assert welcome["conditions"] == [dict(type=aoe2mc.TIMER, timer=5, inverted=False)]
    assert [e["type"] for e in welcome["effects"]] == [aoe2mc.SEND_CHAT, aoe2mc.DISPLAY_INSTRUCTIONS]
    assert welcome["effects"][0]["message"] == "Welcome to the tiny map."
    load, files = aoe2mc.trigger_files(texts["triggers"])
    assert "schedule function aoe2mc:trigger/0 100t replace" in load   # the knight: an area (#649)
    assert "schedule function aoe2mc:trigger/2 1200t replace" in load  # the archer: "Remove Object" (#656)
    assert "data/aoe2mc/function/trigger/0.mcfunction" in files and "data/aoe2mc/function/trigger/2.mcfunction" in files


def test_timer_chat_gives_a_function_and_a_schedule(tmp_path):
    t = trig(3, [(aoe2mc.TIMER, 10)], [(aoe2mc.SEND_CHAT, "<BLUE>Hello, \"Lars\"", -1),
                                       (aoe2mc.DISPLAY_INSTRUCTIONS, "Go north.", 4)])
    aoe2mc.write_datapack(str(tmp_path), [], np.zeros((4, 4), np.int16), triggers=[t])
    assert "schedule function aoe2mc:trigger/3 200t replace" in read(tmp_path, "start.mcfunction")
    assert read(tmp_path, "trigger/3.mcfunction").splitlines() == [
        'tellraw @a {"text": "Hello, \\"Lars\\""}', "title @a times 10 80 20",
        'title @a subtitle {"text": "Go north."}', 'title @a title ""']


def test_disabled_and_other_conditions_give_no_function():
    triggers = [trig(0, [(aoe2mc.TIMER, 5)], [(aoe2mc.SEND_CHAT, "a", -1)], enabled=False),
                trig(1, [(aoe2mc.TIMER, 5), (5, -1)], [(aoe2mc.SEND_CHAT, "b", -1)])]   # no conditions: #2972
    assert aoe2mc.trigger_files(triggers) == ([], {})


def test_looping_timer_schedules_itself_again():
    t = trig(4, [(aoe2mc.TIMER, 3), (aoe2mc.TIMER, 7)], [(aoe2mc.SEND_CHAT, "again", -1)], looping=True)
    load, files = aoe2mc.trigger_files([t])
    assert load == ["schedule function aoe2mc:trigger/4 140t replace"]   # all timers must pass
    assert files["data/aoe2mc/function/trigger/4.mcfunction"].splitlines()[-1] == load[0]
