"""The conditions "OR" and "AND" of the triggers of the converted world (#2765): "OR" splits the conditions into groups,
and the trigger fires when all conditions of one group hold. "AND" is the default between two conditions."""
import contextlib
import io

import aoe2mc
from tools import scenarios

LARGER_OR_EQUAL = 4                                                    # Comparison of AoE2ScenarioParser
CHAT = dict(type=aoe2mc.SEND_CHAT, message="Go", player=-1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
AREA = dict(type=aoe2mc.IN_AREA, timer=0, inverted=False, quantity=1, player=1, area=[1, 2, 2, 3], object=-1,
            group=-1, **{"class": -1})
VALUE = dict(type=aoe2mc.VARIABLE_VALUE, timer=0, inverted=False, quantity=3, variable=2, comparison=LARGER_OR_EQUAL)
OR, AND = (dict(type=k, timer=0, inverted=False) for k in (aoe2mc.OR, aoe2mc.AND))
RUN = "unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3"


def tick(conds, looping=False, stats=None):
    t = dict(id=3, name="t", enabled=True, looping=looping, conditions=conds, effects=[CHAT])
    files = aoe2mc.trigger_files([t], stats=stats)[1]
    return files.get("data/aoe2mc/function/tick.mcfunction", "").splitlines(), files


def test_or_gives_one_tick_line_per_group_with_the_same_function():
    lines, files = tick([AREA, OR, VALUE])
    sel = aoe2mc.area_selector(AREA, 4)
    assert lines == [f"execute if entity {sel} {RUN}", f"execute if score #v2 aoe_var matches 3.. {RUN}"]
    assert files["data/aoe2mc/function/trigger/3.mcfunction"].splitlines()[-1] == "scoreboard players set #3 aoe_trig 1"


def test_and_gives_the_lines_of_no_and():
    assert tick([AREA, AND, VALUE]) == tick([AREA, VALUE])
    assert len(tick([AREA, VALUE])[0]) == 1                            # one group: one line with both tests


def test_the_trigger_runs_once_when_both_groups_hold():
    lines, _ = tick([AREA, OR, VALUE])
    assert all(line.endswith(RUN) for line in lines)                    # the function sets the score: the next line skips
    assert tick([OR, AREA, OR, OR, VALUE, OR]) == tick([AREA, OR, VALUE])   # an empty group does not count


def test_a_looping_or_trigger_fires_again_only_after_no_group_holds():
    lines, _ = tick([AREA, OR, VALUE], looping=True)
    sel = aoe2mc.area_selector(AREA, 4)
    assert lines[2:] == ["scoreboard players set #3.or aoe_trig 0",
                         f"execute if entity {sel} run scoreboard players set #3.or aoe_trig 1",
                         "execute if score #v2 aoe_var matches 3.. run scoreboard players set #3.or aoe_trig 1",
                         "execute if score #3.or aoe_trig matches 0 run scoreboard players reset #3 aoe_trig"]


def test_read_scenario_keeps_the_display_order_of_the_conditions(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Either")
    t.new_condition.objects_in_area(quantity=1, source_player=1, area_x1=1, area_y1=2, area_x2=2, area_y2=3)
    t.new_condition.variable_value(quantity=3, variable=2, comparison=LARGER_OR_EQUAL)
    t.new_condition.or_()
    t.condition_order = [0, 2, 1]                                      # the display order: area, OR, variable
    t.new_effect.send_chat(message="Go")
    src = scenarios.save(scn, str(tmp_path / "o.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trig, = aoe2mc.read_scenario(src)[4]["triggers"]
    assert [c["type"] for c in trig["conditions"]] == [aoe2mc.IN_AREA, aoe2mc.OR, aoe2mc.VARIABLE_VALUE]
    assert len(aoe2mc.trigger_files([trig])[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()) == 2
