"""The trigger effect "Modify Variable by Resource" in the converted world (#2823)."""
import contextlib
import io
from collections import Counter

import aoe2mc
from tools import scenarios

SET, ADD, SUBTRACT, MULTIPLY, DIVIDE = 1, 2, 3, 4, 5                  # Operation of AoE2ScenarioParser
FOOD, WOOD, STONE, GOLD = 0, 1, 2, 3                                   # the tribute_list of the resources


def modify(operation=ADD, player=2, resource=GOLD, variable=3):
    return dict(type=aoe2mc.MODIFY_VARIABLE_BY_RESOURCE, message="", player=player, time=0, object=None,
                tile=[-1, -1], area=[-1] * 4, variable=variable, resource=resource, operation=operation)


def timer(n, effects):
    return dict(id=n, name="t", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=1, inverted=False)], effects=effects)


def test_gold_of_player_2_adds_to_variable_3():
    stats = Counter()
    load, files = aoe2mc.trigger_files([timer(1, [modify()])], stats=stats)
    assert files["data/aoe2mc/function/trigger/1.mcfunction"].splitlines()[0] == \
        "scoreboard players operation #v3 aoe_var += Gold aoe_res2"
    assert "scoreboard players add #v3 aoe_var 0" in load                # the variable starts at 0
    assert stats == Counter({"modify variable by resource": 1})


def test_each_operation_and_player_1():
    lines = [aoe2mc.variable_by_resource_lines(modify(op, 1, FOOD), aoe2mc.Effect(*[None] * 4, Counter(), True, {}, {}))
             for op in (SET, ADD, SUBTRACT, MULTIPLY, DIVIDE)]
    assert lines == [[f"scoreboard players operation #v3 aoe_var {op}= Food aoe_res"] for op in ("", "+", "-", "*", "/")]


def test_a_resource_that_is_no_stock_gives_no_line():
    stats = Counter()
    c = aoe2mc.Effect(*[None] * 4, stats, True, {}, {})
    assert [aoe2mc.variable_by_resource_lines(e, c) for e in (modify(resource=4), modify(resource=-1),
                                                               modify(player=0), modify(variable=-1))] == [[]] * 4
    assert stats == Counter({"modify variable by resource (not supported)": 4})


def test_read_scenario_keeps_the_fields(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Gold")
    t.new_condition.timer(timer=1)
    t.new_effect.modify_variable_by_resource(tribute_list=GOLD, source_player=2, operation=ADD, variable=3)
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        t, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = t["effects"]
    assert (e["type"], e["player"], e["resource"], e["operation"], e["variable"]) == \
        (aoe2mc.MODIFY_VARIABLE_BY_RESOURCE, 2, GOLD, ADD, 3)
