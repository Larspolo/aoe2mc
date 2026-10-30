"""#2859 (epic #2538): the trigger effect "Modify Attribute for Class" puts one change of a combat value of a unit class
("@<ObjectClass>") of a player into the data storage aoe2mc:attributes; the scenario mode of the game program changes
train.stats of each unit type of the class (train.applies, train.CLASSES) and sends the new values to its units."""
import contextlib
import io

import numpy as np
from test_civ_costs import setup
from test_scenario_patrol import trigger
from test_trigger_modify_attribute import ADD, HIT_POINTS, apply

import aoe2mc
from game import train
from tools import scenarios

INFANTRY, CAVALRY, BUILDING = 6, 12, 3                                # ObjectClass of AoE2ScenarioParser


def lines(group, attribute=HIT_POINTS, operation=ADD, quantity=5):
    t = trigger(aoe2mc.MODIFY_ATTRIBUTE_FOR_CLASS)
    t["effects"][0].update(object=None, attribute=attribute, operation=operation, quantity=quantity, group=group,
                           **{"class": -1}, aa=-1)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_one_change_for_the_class():
    assert lines(INFANTRY) == ['data modify storage aoe2mc:attributes list append value "1 @infantry hp 2 5"']
    assert lines(-1) == []                                             # no class


def test_the_infantry_of_the_player_gets_5_more_hit_points_and_the_archer_not():
    _, g = setup("BRITONS")
    _, other = setup("BRITONS")
    g.units.append({"uuid": "u1", "name": "MILITIA"})
    g.soldiers["u2"] = "ARCHER"
    log = apply(g, '["1 @infantry hp 2 5"]')
    for name in ("MILITIA", "SPEARMAN"):
        assert train.stats(g, name).hp == train.stats(other, name).hp + 5
    assert train.stats(g, "ARCHER") == train.stats(other, "ARCHER")
    assert any(c.startswith(f"aoe stats u1 {train.stats(g, 'MILITIA').hp} ") for c in log)
    assert not any(c.startswith("aoe stats u2 ") for c in log)


def test_the_cavalry_class_has_the_camels_and_not_the_cavalry_archers():
    assert train.applies("@cavalry", "KNIGHT") and train.applies("@cavalry", "CAMEL_RIDER")
    assert not train.applies("@cavalry", "CAVALRY_ARCHER") and train.applies("@cavalry_archer", "CAVALRY_ARCHER")
    assert train.applies("@archer", "SKIRMISHER") and not train.applies("@archer", "HAND_CANNONEER")
    assert not train.applies("@building", "MILITIA") and train.applies("MILITIA", "MILITIA")


def test_read_scenario_keeps_the_class_and_the_values(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Stronger")
    t.new_condition.timer(timer=5)
    t.new_effect.modify_attribute_for_class(object_group2=INFANTRY, source_player=1, object_attributes=HIT_POINTS,
                                            operation=ADD, quantity=5)
    src = scenarios.save(scn, str(tmp_path / "c.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trig, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trig["effects"]
    assert (e["group"], e["attribute"], e["operation"], e["quantity"]) == (INFANTRY, HIT_POINTS, ADD, 5)
