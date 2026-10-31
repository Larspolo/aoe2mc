"""The scenario variables in the triggers of the converted world: "Change Variable" and "Variable Value" (#2611)."""
import contextlib
import io
import time
from collections import Counter

import pytest

import aoe2mc
from tools import scenarios

SET, ADD, SUBTRACT, MULTIPLY, DIVIDE = 1, 2, 3, 4, 5                  # Operation of AoE2ScenarioParser
EQUAL, LESS, LARGER, LESS_OR_EQUAL, LARGER_OR_EQUAL = 0, 1, 2, 3, 4    # Comparison


def change(operation, quantity, variable=2):
    return dict(type=aoe2mc.CHANGE_VARIABLE, message="", player=-1, time=0, object=None, tile=[-1, -1],
                area=[-1] * 4, quantity=quantity, variable=variable, operation=operation)


def chat(text="Done"):
    return dict(type=aoe2mc.SEND_CHAT, message=text, player=-1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)


def timer(n, effects):
    return dict(id=n, name="t", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=1, inverted=False)], effects=effects)


def value(n, comparison, quantity, variable=2, looping=False):
    return dict(id=n, name="v", enabled=True, looping=looping, effects=[chat()],
                conditions=[dict(type=aoe2mc.VARIABLE_VALUE, timer=0, inverted=False, quantity=quantity,
                                 variable=variable, comparison=comparison)])


def test_change_variable_adds_to_the_score():
    stats = Counter()
    load, files = aoe2mc.trigger_files([timer(1, [change(ADD, 3)])], stats=stats)
    assert files["data/aoe2mc/function/trigger/1.mcfunction"].splitlines() == ["scoreboard players add #v2 aoe_var 3"]
    assert load[:2] == ["scoreboard objectives add aoe_var dummy", "scoreboard players add #v2 aoe_var 0"]
    assert stats == Counter({"change variable": 1})


def ctx(stats):
    return aoe2mc.Effect(None, 4, None, None, stats, True, {}, {})       # the context of a trigger (#2613)


def test_the_operations():
    lines = [aoe2mc.variable_lines(change(op, 4), ctx(Counter())) for op in (SET, SUBTRACT, MULTIPLY, DIVIDE)]
    assert lines[:2] == [["scoreboard players set #v2 aoe_var 4"], ["scoreboard players remove #v2 aoe_var 4"]]
    assert lines[2] == ["scoreboard players set #c4 aoe_var 4", "scoreboard players operation #v2 aoe_var *= #c4 aoe_var"]
    assert lines[3][1] == "scoreboard players operation #v2 aoe_var /= #c4 aoe_var"
    stats = Counter()
    assert aoe2mc.variable_lines(change(DIVIDE, 0), ctx(stats)) == [] and stats == Counter({"change variable (not supported)": 1})


def test_variable_value_fires_in_the_tick_function_once():
    load, files = aoe2mc.trigger_files([value(5, LARGER_OR_EQUAL, 3)])
    assert files["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        "execute if score #v2 aoe_var matches 3.. unless score #5 aoe_trig matches 1 run function aoe2mc:trigger/5"]
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines()[-1] == "scoreboard players set #5 aoe_trig 1"
    assert "scoreboard objectives add aoe_var dummy" in load and "scoreboard objectives add aoe_trig dummy" in load


def test_the_comparisons():
    ranges = [aoe2mc.variable_range(value(1, c, 3)["conditions"][0]) for c in range(5)]
    assert ranges == ["3", "..2", "4..", "..3", "3.."]


def test_a_looping_variable_trigger_resets_when_the_value_changes():
    tick = aoe2mc.trigger_files([value(5, EQUAL, 1, looping=True)])[1]["data/aoe2mc/function/tick.mcfunction"]
    assert tick.splitlines()[1] == "execute unless score #v2 aoe_var matches 1 run scoreboard players reset #5 aoe_trig"


def test_read_scenario_keeps_the_variable_fields(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Add")
    t.new_condition.timer(timer=1)
    t.new_effect.change_variable(quantity=3, operation=ADD, variable=2)
    t = scn.trigger_manager.add_trigger("Check")
    t.new_condition.variable_value(quantity=3, variable=2, comparison=LARGER_OR_EQUAL)
    t.new_effect.send_chat(message="Three")
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        add, check = aoe2mc.read_scenario(src)[4]["triggers"]
    assert {k: add["effects"][0][k] for k in ("quantity", "operation", "variable")} == \
        dict(quantity=3, operation=ADD, variable=2)
    c, = check["conditions"]
    assert (c["type"], c["quantity"], c["variable"], c["comparison"]) == (aoe2mc.VARIABLE_VALUE, 3, 2, LARGER_OR_EQUAL)


@pytest.mark.mc
def test_the_first_trigger_fires_the_second_on_a_server(tmp_path):
    from test_paper import paper_reachable

    from game import run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Add")
    t.new_condition.timer(timer=2)
    t.new_effect.change_variable(quantity=3, operation=ADD, variable=2)
    t = scn.trigger_manager.add_trigger("Check")
    t.new_condition.variable_value(quantity=3, variable=2, comparison=LARGER_OR_EQUAL)
    t.new_effect.send_chat(message="Three")
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    world = str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)

    def score(holder, objective):
        out = game.command(f"scoreboard players get {holder} {objective}")
        return int(out.split(" has ")[1].split()[0]) if " has " in out else None

    with run.Game(world) as game:
        game.forceload()
        assert score("#v2", "aoe_var") in (0, 3)
        end = time.time() + 15
        while time.time() < end and score("#1", "aoe_trig") != 1:
            time.sleep(0.2)
        assert score("#v2", "aoe_var") == 3
        assert score("#1", "aoe_trig") == 1                            # the second trigger (id 1) fired once
