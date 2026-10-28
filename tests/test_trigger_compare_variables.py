"""The condition "Compare Variables" in the triggers of the converted world (#2698): two scenario variables."""
import contextlib
import io

import aoe2mc
from tools import scenarios

EQUAL, LESS, LARGER, LESS_OR_EQUAL, LARGER_OR_EQUAL, NOT_EQUAL = range(6)   # Comparison


def compare(comparison, variable=2, variable2=3, inverted=False, looping=False):
    return dict(id=5, name="c", enabled=True, looping=looping,
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Hi", player=-1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)],
                conditions=[dict(type=aoe2mc.COMPARE_VARIABLES, timer=0, inverted=inverted, variable=variable,
                                 variable2=variable2, comparison=comparison)])


def tick(trigger):
    return aoe2mc.trigger_files([trigger])[1]["data/aoe2mc/function/tick.mcfunction"]


def test_the_operators_compare_the_two_variables():
    lines = [tick(compare(c)).split(" unless ")[0] for c in range(LARGER_OR_EQUAL + 1)]
    assert lines == ["execute if score #v2 aoe_var = #v3 aoe_var", "execute if score #v2 aoe_var < #v3 aoe_var",
                     "execute if score #v2 aoe_var > #v3 aoe_var", "execute if score #v2 aoe_var <= #v3 aoe_var",
                     "execute if score #v2 aoe_var >= #v3 aoe_var"]


def test_not_equal_fires_unless_the_variables_are_equal():
    assert tick(compare(NOT_EQUAL)).startswith("execute unless score #v2 aoe_var = #v3 aoe_var unless score #5 aoe_trig")


def test_inverted_turns_the_test_into_unless():
    assert tick(compare(LESS, inverted=True)).startswith("execute unless score #v2 aoe_var < #v3 aoe_var unless score")
    assert tick(compare(NOT_EQUAL, inverted=True)).startswith("execute if score #v2 aoe_var = #v3 aoe_var unless score")


def test_the_trigger_fires_once_and_the_variables_are_loaded():
    load, files = aoe2mc.trigger_files([compare(LESS)])
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines()[-1] == "scoreboard players set #5 aoe_trig 1"
    assert "scoreboard players add #v2 aoe_var 0" in load and "scoreboard players add #v3 aoe_var 0" in load


def test_a_looping_trigger_resets_when_the_test_fails():
    assert tick(compare(EQUAL, looping=True)).splitlines()[1] == \
        "execute unless score #v2 aoe_var = #v3 aoe_var run scoreboard players reset #5 aoe_trig"


def test_a_missing_variable_is_not_converted():
    assert aoe2mc.compare_test(dict(variable=-1, variable2=3, comparison=LESS)) is None
    assert aoe2mc.trigger_files([compare(LESS, variable2=-1)])[1] == {}


def test_read_scenario_keeps_the_two_variables(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Compare")
    t.new_condition.compare_variables(variable=2, variable2=3, comparison=LESS, inverted=0)
    t.new_effect.send_chat(message="Less")
    src = scenarios.save(scn, str(tmp_path / "c.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        c, = aoe2mc.read_scenario(src)[4]["triggers"][0]["conditions"]
    assert (c["type"], c["variable"], c["variable2"], c["comparison"]) == (aoe2mc.COMPARE_VARIABLES, 2, 3, LESS)
