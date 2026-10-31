"""A base scenario of format 1.36 to 1.54 has no legacy_execution_order option (AoE2ScenarioParser: since 1.55). The
scenario runs its triggers in the stored order, as its game did, and the reader keeps the scenario (#5071)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.effects import EffectId  # noqa: E402
from AoE2ScenarioParser.exceptions.asp_exceptions import UnsupportedAttributeError  # noqa: E402
from AoE2ScenarioParser.objects.managers.option_manager import OptionManager  # noqa: E402

import aoe2mc  # noqa: E402


def old_format(monkeypatch):
    """The parser of a format before 1.55: reading legacy_execution_order raises, writing it is ignored."""
    def get(self):
        raise UnsupportedAttributeError("The property 'legacy_execution_order' is supported since: 1.55.")
    monkeypatch.setattr(OptionManager, "legacy_execution_order", property(get, lambda self, v: None), raising=False)


def two_triggers(tmp_path):
    scn = scenarios.new_scenario(24)
    for name in ("first stored", "second stored"):
        t = scn.trigger_manager.add_trigger(name)
        t.new_condition.timer(timer=5)
        t._add_effect(EffectId.SEND_CHAT, message=name)
    scn.trigger_manager.trigger_display_order = [1, 0]
    return scenarios.save(scn, str(tmp_path / "old.aoe2scenario"))


def test_a_scenario_without_the_option_keeps_the_stored_trigger_order(tmp_path, monkeypatch):
    path = two_triggers(tmp_path)
    old_format(monkeypatch)
    triggers = aoe2mc.read_scenario(path)[4]["triggers"]
    assert [t["name"] for t in triggers] == ["first stored", "second stored"]


def test_a_scenario_without_the_option_keeps_the_stored_effect_order(tmp_path, monkeypatch):
    scn = scenarios.new_scenario(24)
    t = scn.trigger_manager.add_trigger("Timer")
    t.new_condition.timer(timer=15)
    t._add_effect(EffectId.SEND_CHAT, message="stored first, shown second")
    t._add_effect(EffectId.SEND_CHAT, message="stored second, shown first")
    t.effect_order = [1, 0]
    path = scenarios.save(scn, str(tmp_path / "effects.aoe2scenario"))
    old_format(monkeypatch)
    effects = aoe2mc.read_scenario(path)[4]["triggers"][0]["effects"]
    assert [e["message"] for e in effects] == ["stored first, shown second", "stored second, shown first"]
