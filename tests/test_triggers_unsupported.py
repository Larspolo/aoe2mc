"""tools/triggers.py MAP: the AoE2 DE trigger types that the converter and the game program do not support have a row
with the reason, so that the epic #2538 checks its whole scope from one table (#2869)."""
import pytest

import triggers

UNSUPPORTED = [("condition", n) for n in ("AI_SIGNAL", "AI_SIGNAL_MULTIPLAYER", "HERO_POWER_CAST",
                                          "LOCAL_TECH_RESEARCHED", "OBJECT_HAS_TARGET", "OBJECT_SELECTED_MULTIPLAYER",
                                          "SCRIPT_CALL")] + \
              [("effect", n) for n in ("ACKNOWLEDGE_AI_SIGNAL", "ACKNOWLEDGE_MULTIPLAYER_AI_SIGNAL", "AI_SCRIPT_GOAL",
                                       "CHANGE_OBJECT_CAPTION", "CHANGE_OBJECT_CIVILIZATION_NAME",
                                       "CHANGE_OBJECT_DESCRIPTION", "CHANGE_OBJECT_ICON", "CHANGE_OBJECT_PLAYER_NAME",
                                       "CHANGE_TECHNOLOGY_DESCRIPTION", "CHANGE_TECHNOLOGY_HOTKEY",
                                       "CHANGE_TECHNOLOGY_ICON", "DISABLE_OBJECT_DELETION", "ENABLE_OBJECT_DELETION",
                                       "RESEARCH_LOCAL_TECHNOLOGY", "SCRIPT_CALL", "USE_ADVANCED_BUTTONS")]


@pytest.mark.parametrize("key", UNSUPPORTED)
def test_an_unsupported_trigger_type_has_a_row_with_its_reason(key):
    row = triggers.MAP[key]
    assert row.startswith("not supported: ") and len(row) > len("not supported: ") + 5, key
