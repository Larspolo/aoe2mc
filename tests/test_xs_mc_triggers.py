"""#5693 (epic #5119): the Script Call effect and condition run their XS code as datapack functions (xs/<name>/...);
the game program keeps its scores (#a aoe_xs)."""
from collections import Counter

from test_trigger_objects import effect, trig
from test_xs_condition import cond

import aoe2mc

EFFECT = "void f() { xsSetTriggerVariable(1, 5); }"
CONDITION = "bool c() { return (true); }"


def converted(t):
    _, files = aoe2mc.trigger_files([t], stats=Counter())
    return "\n".join(v for v in files.values() if isinstance(v, str))


def test_the_trigger_calls_the_function_of_its_effect_and_tests_the_condition_result():
    eff = effect(aoe2mc.XS_EFFECT) | {"message": EFFECT}
    t = dict(trig([eff]), conditions=[cond(CONDITION)])
    text = converted(t)
    assert "function aoe2mc:xs/e7_0/f/f" in text
    assert "function aoe2mc:xs/c7_0/f/c" in text
    assert "scoreboard players operation #c7.0 aoe_xs = #r.c aoe_xs" in text
    assert "if score #c7.0 aoe_xs matches 1" in text


def test_the_function_files_of_a_code_have_its_own_prefix():
    eff = effect(aoe2mc.XS_EFFECT) | {"message": EFFECT}
    _, files = aoe2mc.trigger_files([trig([eff])], stats=Counter())
    assert "data/aoe2mc/function/xs/e7_0/f/f.mcfunction" in files
    assert "data/aoe2mc/function/xs/e7_0/main.mcfunction" in files


def test_a_part_with_no_datapack_form_gives_one_warning_and_the_effect_still_runs(capsys):
    eff = effect(aoe2mc.XS_EFFECT) | {"message": "void f() { noSuchCall(1); xsSetTriggerVariable(1, 5); }"}
    text = converted(trig([eff]))
    out = capsys.readouterr().out
    assert out.count("noSuchCall") == 1
    assert "function aoe2mc:xs/e7_0/f/f" in text
