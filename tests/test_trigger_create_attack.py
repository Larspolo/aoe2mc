"""#2855 (epic #2538): the trigger effects "Create Object Attack" and "Create Object Armor" add the value to the attack
or armor class of the unit type of a player (AoE2 adds the entries of one class): the change goes into the data
storage aoe2mc:attributes, and the scenario mode of the game program applies it (train.stats)."""
import contextlib
import io
import os
import sys

import numpy as np

import aoe2mc
import scenarios
from test_civ_costs import setup
from test_trigger_modify_attribute import apply

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
from game import combat, train  # noqa: E402

MELEE, PIERCE = 4, 3


def stored(tmp_path, kind="create_object_attack", cls=MELEE, value=3):
    from AoE2ScenarioParser.datasets.players import PlayerId
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(24)
    t = scn.trigger_manager.add_trigger("Stronger")
    t.new_condition.timer(timer=5)
    getattr(t.new_effect, kind)(object_list_unit_id=UnitInfo.MILITIA.ID, source_player=PlayerId.ONE,
                                armour_attack_class=cls, armour_attack_quantity=value)
    path = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        texts = aoe2mc.read_scenario(path)[4]
    files = aoe2mc.trigger_files(texts["triggers"], 4, np.full((96, 96), 70, np.int16))[1]
    return "\n".join(v for k, v in files.items() if k.startswith("data/aoe2mc/function/trigger/"))


def test_the_converted_effect_stores_the_change(tmp_path):
    assert 'data modify storage aoe2mc:attributes list append value "1 MILITIA attack 2 3"' in stored(tmp_path)
    assert '"1 MILITIA pierce 2 2"' in stored(tmp_path, "create_object_armor", PIERCE, 2)


def test_a_bonus_class_has_no_line(tmp_path):
    assert "aoe2mc:attributes" not in stored(tmp_path, cls=27)


def test_the_militia_of_the_player_does_3_more_melee_damage():
    _, g = setup("BRITONS")
    _, other = setup("BRITONS")
    target = combat.stats("VILLAGER_MALE")._replace(melee=0)           # no melee armor: each point counts
    before = combat.damage("MILITIA", "VILLAGER_MALE", train.stats(g, "MILITIA"), target)
    apply(g, '["1 MILITIA attack 2 3"]')
    assert combat.damage("MILITIA", "VILLAGER_MALE", train.stats(g, "MILITIA"), target) == before + 3
    assert combat.damage("MILITIA", "VILLAGER_MALE", train.stats(other, "MILITIA"), target) == before
