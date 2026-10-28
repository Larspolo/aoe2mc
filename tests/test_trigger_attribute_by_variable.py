"""#2856 (epic #2538): the trigger effect "Modify Attribute by Variable" changes a combat value of a unit type of a
player by the score #v<N> of aoe_var: a macro function puts the score into the line of the storage aoe2mc:attributes."""
import re

import numpy as np
from test_civ_costs import setup
from test_scenario_patrol import trigger
from test_trigger_modify_attribute import ADD, HIT_POINTS, LINE_OF_SIGHT, apply

import aoe2mc
from game import train

FUNCTION = "data/aoe2mc/function/attribute_by_variable.mcfunction"


def convert(attribute=HIT_POINTS, operation=ADD, variable=2):
    t = trigger(aoe2mc.MODIFY_ATTRIBUTE_BY_VARIABLE)
    t["effects"][0].update(object=("U", "MILITIA"), attribute=attribute, operation=operation, variable=variable,
                           **{"class": -1})
    load, files = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))
    return load, files


def run(lines, macro, scores):
    """The storage line that the commands of the trigger function give with the scores {holder: value}."""
    storage = {}
    for cmd in lines:
        if m := re.fullmatch(r'data modify storage aoe2mc:attribute_by_variable (\w+) set value "(.*)"', cmd):
            storage[m[1]] = m[2]
        elif m := re.fullmatch(r"execute store result storage aoe2mc:attribute_by_variable (\w+) int 1 run "
                               r"scoreboard players get (\S+) aoe_var", cmd):
            storage[m[1]] = scores.get(m[2], 0)
        else:
            assert cmd == "function aoe2mc:attribute_by_variable with storage aoe2mc:attribute_by_variable", cmd
            line = re.sub(r"\$\((\w+)\)", lambda k: str(storage[k[1]]), macro.lstrip("$").strip())
    return re.fullmatch(r'data modify storage aoe2mc:attributes list append value (".*")', line)[1]


def test_the_trigger_function_puts_the_variable_into_the_storage_line():
    load, files = convert()
    lines = files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines()
    assert lines == ['data modify storage aoe2mc:attribute_by_variable head set value "1 MILITIA hp 2"',
                     "execute store result storage aoe2mc:attribute_by_variable q int 1 run scoreboard players get "
                     "#v2 aoe_var",
                     "function aoe2mc:attribute_by_variable with storage aoe2mc:attribute_by_variable"]
    assert files[FUNCTION].startswith("$data modify storage aoe2mc:attributes list append value ")
    assert "scoreboard objectives add aoe_var dummy" in load
    assert run(lines, files[FUNCTION], {"#v2": 10}) == '"1 MILITIA hp 2 10"'


def test_an_attribute_that_the_game_program_does_not_have_has_no_function():
    _, files = convert(attribute=LINE_OF_SIGHT)
    assert not files.get("data/aoe2mc/function/trigger/7.mcfunction", "").strip() and FUNCTION not in files
    assert FUNCTION not in convert(variable=-1)[1]


def test_the_militia_of_player_1_gets_the_value_of_the_variable():
    _, files = convert()
    line = run(files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines(), files[FUNCTION], {"#v2": 10})
    _, g = setup("BRITONS")
    before = train.stats(g, "MILITIA").hp
    apply(g, f"[{line}]")
    assert train.stats(g, "MILITIA").hp == before + 10
