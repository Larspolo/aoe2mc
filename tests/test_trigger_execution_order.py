"""Triggers and effects run in their display order, as AoE2 DE does by default (#3087). The stored order is kept
for a scenario with "Run triggers and effects in display order" off (legacy_execution_order)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.effects import EffectId  # noqa: E402

import aoe2mc  # noqa: E402


def two_effects(tmp_path, legacy=False):
    scn = scenarios.new_scenario(24)
    scn.option_manager.legacy_execution_order = legacy
    t = scn.trigger_manager.add_trigger("Timer")
    t.new_condition.timer(timer=15)
    t._add_effect(EffectId.SEND_CHAT, message="stored first, shown second")
    t._add_effect(EffectId.SEND_CHAT, message="stored second, shown first")
    t.effect_order = [1, 0]
    return scenarios.save(scn, str(tmp_path / "order.aoe2scenario"))


def test_the_effects_run_in_the_display_order(tmp_path):
    path = two_effects(tmp_path)
    effects = aoe2mc.read_scenario(path)[4]["triggers"][0]["effects"]
    assert [e["message"] for e in effects] == ["stored second, shown first", "stored first, shown second"]


def test_the_effects_keep_the_stored_order_in_legacy_mode(tmp_path):
    path = two_effects(tmp_path, legacy=True)
    effects = aoe2mc.read_scenario(path)[4]["triggers"][0]["effects"]
    assert [e["message"] for e in effects] == ["stored first, shown second", "stored second, shown first"]


def test_the_triggers_run_in_the_display_order(tmp_path):
    scn = scenarios.new_scenario(24)
    for name, sec in (("first stored", 5), ("second stored", 5)):
        t = scn.trigger_manager.add_trigger(name)
        t.new_condition.timer(timer=sec)
        t._add_effect(EffectId.SEND_CHAT, message=name)
    scn.trigger_manager.trigger_display_order = [1, 0]
    path = scenarios.save(scn, str(tmp_path / "triggers.aoe2scenario"))
    triggers = aoe2mc.read_scenario(path)[4]["triggers"]
    assert [t["name"] for t in triggers] == ["second stored", "first stored"]
    load, _ = aoe2mc.trigger_files(triggers)
    scheduled = [line for line in load if "schedule function" in line]
    assert scheduled[0].startswith("schedule function aoe2mc:trigger/1 ")
