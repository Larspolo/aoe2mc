"""aoe2mc.EFFECT_KEYS: the keys of each trigger effect of read_scenario come from one table, one line per effect in
alphabetical order (#2792): parallel trigger tickets conflicted in one expression of read_scenario."""
import ast
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import aoe2mc  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.effects import EffectId  # noqa: E402
from AoE2ScenarioParser.datasets.techs import TechInfo  # noqa: E402
from AoE2ScenarioParser.datasets.units import UnitInfo  # noqa: E402

COMMON = {"type", "message", "player", "time", "object", "tile", "area"}


def test_the_lines_of_effect_keys_are_in_alphabetical_order():
    tree = ast.parse(inspect.getsource(aoe2mc))
    table = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], "id", None) == "EFFECT_KEYS")
    names = [k.id for k in table.keys]
    assert names == sorted(names), "put each new line of EFFECT_KEYS in alphabetical order, not at the end"


def test_each_effect_gets_the_keys_of_its_line(tmp_path):
    scn = scenarios.new_scenario(24)
    t = scn.trigger_manager.add_trigger("All")
    t.new_condition.timer(timer=5)
    for eid in sorted(aoe2mc.EFFECT_KEYS):
        t._add_effect(EffectId(eid), quantity=7, target_player=3, trigger_id=0, timer=2,
                      object_list_unit_id_2=UnitInfo.KNIGHT.ID, technology=TechInfo.LOOM.ID)
    t._add_effect(EffectId.SEND_CHAT, message="hi")
    path = scenarios.save(scn, str(tmp_path / "keys.aoe2scenario"))
    texts = aoe2mc.read_scenario(path)[4]
    effects = {e["type"]: e for e in texts["triggers"][0]["effects"]}
    for eid, keys in aoe2mc.EFFECT_KEYS.items():
        assert set(effects[eid]) == COMMON | set(keys), EffectId(eid).name
    assert set(effects[EffectId.SEND_CHAT]) == COMMON                 # no line: only the common keys
    assert effects[aoe2mc.DAMAGE_OBJECT]["quantity"] == 7
    assert effects[aoe2mc.TRIBUTE]["target"] == 3
    assert effects[aoe2mc.REPLACE_OBJECT]["object2"] is not None      # the kind of the knight, as "object"
    assert effects[aoe2mc.RESEARCH_TECHNOLOGY]["technology"] == "LOOM"
    assert effects[aoe2mc.PLAY_SOUND]["sound"] == ""
