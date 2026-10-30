"""#2705 (epic #2538): the trigger effect "Change Object Stance" tags the units of a player in an area and puts a stance
order into the data storage aoe2mc:orders; the scenario mode of the game program sets the stance with the plugin."""
import numpy as np
from test_scenario_patrol import play, trigger

import aoe2mc


def test_the_trigger_function_tags_the_units_and_stores_the_stance():
    t = trigger(aoe2mc.CHANGE_OBJECT_STANCE)
    t["effects"][0]["stance"] = 1                                       # defensive
    lines = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1][
        "data/aoe2mc/function/trigger/7.mcfunction"].splitlines()
    assert lines[0].endswith(" add aoe_order7_0") and "tag=aoe2mc.p1," in lines[0]
    assert lines[3] == 'data modify storage aoe2mc:orders list append value "stance aoe_order7_0 1"'


def test_a_stance_with_no_value_has_no_lines():
    assert aoe2mc.trigger_files([trigger(aoe2mc.CHANGE_OBJECT_STANCE)], 4, np.full((64, 64), 70, np.int16))[1] == {}


def test_the_scenario_mode_gives_the_tagged_units_the_defensive_stance():
    g, log = play('Storage aoe2mc:orders has the following contents: ["stance aoe_order7_0 1"]')
    assert log.index("aoe stance @e[tag=aoe_order7_0] defensive") < log.index("tag @e[tag=aoe_order7_0] remove aoe_order7_0")
    assert not any(c.startswith("aoe moveto") for c in log) and g.patrols == []
