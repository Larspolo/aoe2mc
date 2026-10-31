"""The trigger effect "Modify Variable by Variable" in the converted world (#2713)."""
import contextlib
import io
import time
from collections import Counter

import pytest

import aoe2mc
from tools import scenarios

SET, ADD, SUBTRACT, MULTIPLY, DIVIDE = 1, 2, 3, 4, 5                  # Operation of AoE2ScenarioParser


def modify(operation, variable=2, variable2=3):
    return dict(type=aoe2mc.MODIFY_VARIABLE_BY_VARIABLE, message="", player=-1, time=0, object=None, tile=[-1, -1],
                area=[-1] * 4, variable=variable, variable2=variable2, operation=operation)


def timer(n, effects):
    return dict(id=n, name="t", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=1, inverted=False)], effects=effects)


def test_each_operation_is_one_scoreboard_operation():
    stats = Counter()
    load, files = aoe2mc.trigger_files([timer(n, [modify(n)]) for n in (SET, ADD, SUBTRACT, MULTIPLY, DIVIDE)],
                                       stats=stats)
    lines = [files[f"data/aoe2mc/function/trigger/{n}.mcfunction"].splitlines()[0] for n in range(1, 6)]
    assert lines == [f"scoreboard players operation #v2 aoe_var {op}= #v3 aoe_var" for op in ("", "+", "-", "*", "/")]
    assert stats == Counter({"modify variable by variable": 5})


def test_both_variables_start_at_0():
    load, _ = aoe2mc.trigger_files([timer(1, [modify(ADD, 4, 7)])])
    assert load[:3] == ["scoreboard objectives add aoe_var dummy", "scoreboard players add #v4 aoe_var 0",
                        "scoreboard players add #v7 aoe_var 0"]


def test_a_missing_variable_or_operation_gives_no_line():
    stats = Counter()
    load, files = aoe2mc.trigger_files([timer(1, [modify(ADD, -1), modify(ADD, 2, -1), modify(9)])], stats=stats)
    assert "scoreboard players operation" not in files.get("data/aoe2mc/function/trigger/1.mcfunction", "")
    assert stats == Counter({"modify variable by variable (not supported)": 3})


def test_read_scenario_keeps_both_variables(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Copy")
    t.new_condition.timer(timer=1)
    t.new_effect.modify_variable_by_variable(variable=2, operation=MULTIPLY, variable2=5)
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        t, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = t["effects"]
    assert (e["type"], e["variable"], e["operation"], e["variable2"]) == (aoe2mc.MODIFY_VARIABLE_BY_VARIABLE, 2, MULTIPLY, 5)


@pytest.mark.mc
def test_the_score_on_a_server(tmp_path):
    from test_paper import paper_reachable

    from game import run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Set")
    t.new_condition.timer(timer=1)
    t.new_effect.change_variable(quantity=6, operation=SET, variable=2)
    t.new_effect.change_variable(quantity=4, operation=SET, variable=3)
    t = scn.trigger_manager.add_trigger("Multiply")
    t.new_condition.timer(timer=3)
    t.new_effect.modify_variable_by_variable(variable=2, operation=MULTIPLY, variable2=3)
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    world = str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)

    def score(holder):
        out = game.command(f"scoreboard players get {holder} aoe_var")
        return int(out.split(" has ")[1].split()[0]) if " has " in out else None

    with run.Game(world) as game:
        game.forceload()
        end = time.time() + 15
        while time.time() < end and score("#v2") != 24:
            time.sleep(0.2)
        assert (score("#v2"), score("#v3")) == (24, 4)
