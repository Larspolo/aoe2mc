"""tools/triggers.py counts the trigger conditions and effects of scenarios and campaigns (#646)."""
from collections import Counter

import scenarios
import triggers
from test_campaign import campaign


def test_count_of_a_timer_trigger(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Hello")
    t.new_condition.timer(timer=10)
    t.new_effect.send_chat(source_player=1, message="Hello")
    path = scenarios.save(scn, str(tmp_path / "timer.aoe2scenario"))
    assert triggers.count(path) == Counter({("condition", "TIMER"): 1, ("effect", "SEND_CHAT"): 1})
    camp = campaign(tmp_path / "c.aoe2campaign", [path, path])
    assert triggers.count(camp) == Counter({("condition", "TIMER"): 2, ("effect", "SEND_CHAT"): 2})
    assert triggers.count(tmp_path / "old.scx") == Counter({("not read", ".scx"): 1})


def test_triggers_scenario_and_table(tmp_path):
    n = triggers.count(scenarios.triggers(str(tmp_path / "t.aoe2scenario")))
    assert n[("condition", "TIMER")] == 2 and n[("condition", "OBJECTS_IN_AREA")] == 1
    assert n[("effect", "CREATE_OBJECT")] == n[("effect", "REMOVE_OBJECT")] == n[("effect", "DISPLAY_INSTRUCTIONS")] == 1
    rows = triggers.table(n).splitlines()
    assert rows[2] == f"| condition | `TIMER` | 2 | {triggers.MAP[('condition', 'TIMER')]} |"   # the most common first
    assert all(r.count("|") == 5 for r in rows)
    text = triggers.MAP.get(("condition", "OBJECT_SELECTED"), "not supported: no ticket yet")
    assert f"| condition | `OBJECT_SELECTED` | 0 | {text} |" in rows   # a type that no scenario has
