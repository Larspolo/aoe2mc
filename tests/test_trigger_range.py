"""#2767 (epic #2538): the trigger effect "Change Object Range" tags the units of a player in an area and puts a range
order into the data storage aoe2mc:orders; the scenario mode of the game program sends the new range of each tagged
ranged unit with the plugin (`aoe range`)."""
import numpy as np
from test_scenario_mode import game
from test_scenario_patrol import scenario, trigger

import aoe2mc
from game import combat


def lines(**effect):
    t = trigger(aoe2mc.CHANGE_OBJECT_RANGE)
    t["effects"][0].update(effect)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_tags_the_units_and_stores_the_range_order():
    out = lines(operation=2, quantity=2)                                 # add 2 tiles
    assert out[0].endswith(" add aoe_order7_0") and "tag=aoe2mc.p1," in out[0] and "x=8," in out[0]
    assert out[3] == 'data modify storage aoe2mc:orders list append value "range aoe_order7_0 2 2"'


def test_a_range_with_no_operation_has_no_lines():
    assert lines() == [] and lines(operation=9, quantity=2) == []


def run(order, tagged):
    """scenario.orders with one stored order: own archers a1, a2, an own militia m1 and an archer e1 of player 2;
    the units in tagged have the tag."""
    server, g, _ = game({"1": {}, "2": {}})
    g.soldiers.update({"a1": "ARCHER", "a2": "ARCHER", "m1": "MILITIA"})
    g.data["objects"].append({"kind": "unit", "name": "ARCHER", "player": 2, "uuid": "e1"})
    command, stored = server.command, [f'Storage aoe2mc:orders has the following contents: ["{order}"]']

    def answer(cmd):
        if cmd.startswith("data remove storage aoe2mc:orders"):
            stored[0] = "Found no elements matching list"
        if cmd.startswith("data get storage aoe2mc:orders"):
            return stored[0]
        if cmd.startswith("execute as "):
            server.log.append(cmd)
            return "Test passed, count: 1" if cmd.split()[2] in tagged else "Test failed"
        return command(cmd)
    server.command = answer
    scenario.orders(g)
    return g, [c for c in server.log if c.startswith(("aoe range", "tag "))]


def reach(log, uuid):
    return [float(c.split()[3]) for c in log if c.startswith(f"aoe range {uuid} ")]


def test_a_tagged_archer_gets_its_range_plus_2_and_the_others_keep_theirs():
    g, log = run("range aoe_order7_0 2 2", {"a1", "m1", "e1"})
    archer = combat.stats("ARCHER").range
    assert reach(log, "a1") == [(archer + 2) * g.map.T] and reach(log, "e1") == [(archer + 2) * g.map.T]
    assert reach(log, "a2") == [] and reach(log, "m1") == []           # no tag; a melee unit gets no shot
    assert log[-1] == "tag @e[tag=aoe_order7_0] remove aoe_order7_0"


def test_set_and_multiply():
    g, log = run("range aoe_order7_0 1 7", {"a1"})
    assert reach(log, "a1") == [7 * g.map.T]
    g, log = run("range aoe_order7_0 4 2", {"a1"})
    assert reach(log, "a1") == [combat.stats("ARCHER").range * 2 * g.map.T]
