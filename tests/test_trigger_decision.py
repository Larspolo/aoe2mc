"""#2886 (epic #2538): the trigger effect "Create Decision". The converter shows the question and its two options in the
chat of each player (tellraw with click events); a click runs `/trigger aoe_decision set <id × 10 + option>`, and the
tick function keeps the last click in #last of aoe_decision."""
import json
from collections import Counter

import numpy as np

import aoe2mc


def effect(message="Help the king?", option1="Yes", option2="No", decision=2):
    return dict(type=aoe2mc.CREATE_DECISION, message=message, player=1, time=0, object=None, tile=[-1, -1],
                area=[-1] * 4, decision=decision, option1=option1, option2=option2)


def convert(*effects, stats=None):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=list(effects),
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    return aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16), stats=stats)


def test_the_question_has_two_click_commands_and_enables_the_trigger():
    load, files = convert(effect())
    enable, tellraw = files["data/aoe2mc/function/trigger/8.mcfunction"].splitlines()
    assert enable == "scoreboard players enable @a aoe_decision"
    text = json.loads(tellraw.removeprefix("tellraw @a "))
    assert text[0] == "Help the king?"
    assert [(t["text"], t["click_event"]) for t in text[2::2]] == [
        ("[Yes]", {"action": "run_command", "command": "/trigger aoe_decision set 21"}),
        ("[No]", {"action": "run_command", "command": "/trigger aoe_decision set 22"})]
    assert "scoreboard objectives add aoe_decision trigger" in load


def test_the_tick_function_keeps_the_last_click():
    tick = convert(effect())[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert tick == aoe2mc.DECISION_TICK
    assert "#last aoe_decision = @s aoe_decision" in tick[0]


def test_quotes_are_escaped_and_color_tags_removed():
    tellraw = convert(effect(message='<RED>Say "yes"?'))[1]["data/aoe2mc/function/trigger/8.mcfunction"].splitlines()[1]
    assert json.loads(tellraw.removeprefix("tellraw @a "))[0] == 'Say "yes"?'


def test_only_string_ids_are_not_supported():
    stats = Counter()
    load, files = convert(effect(option1=""), effect(message=""), stats=stats)
    assert "data/aoe2mc/function/tick.mcfunction" not in files
    assert stats["create decision (no text, not supported yet)"] == 2
