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

COMMON = {"type", "message", "player", "time", "object", "tile", "area"}


def test_the_lines_of_effect_keys_are_in_alphabetical_order():
    tree = ast.parse(inspect.getsource(aoe2mc))
    table = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], "id", None) == "EFFECT_KEYS")
    names = [k.id for k in table.keys]
    assert names == sorted(names), "put each new line of EFFECT_KEYS in alphabetical order, not at the end"


def test_an_effect_gets_the_keys_of_its_line(tmp_path, monkeypatch):
    monkeypatch.setitem(aoe2mc.EFFECT_KEYS, aoe2mc.SEND_CHAT, {
        "quantity": "quantity", "technology": lambda e, kinds, techs: techs.get(e.technology, str(e.technology))})
    scn = scenarios.new_scenario(24)
    t = scn.trigger_manager.add_trigger("All")
    t.new_condition.timer(timer=5)
    t._add_effect(EffectId.SEND_CHAT, message="hi", quantity=7, technology=TechInfo.LOOM.ID)
    t._add_effect(EffectId.DISPLAY_INSTRUCTIONS, message="hi", quantity=7)
    path = scenarios.save(scn, str(tmp_path / "keys.aoe2scenario"))
    chat, text = aoe2mc.read_scenario(path)[4]["triggers"][0]["effects"]
    assert set(chat) == COMMON | {"quantity", "technology"} and (chat["quantity"], chat["technology"]) == (7, "LOOM")
    assert set(text) == COMMON                                         # no line: only the common keys
