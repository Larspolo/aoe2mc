"""Each control that a tutorial step names exists in the game program (#5164)."""
import pytest

from game import build, tutorial


@pytest.mark.parametrize("row", tutorial.STEPS, ids=lambda r: r["name"])
def test_each_control_of_a_step_is_a_known_item(row):
    assert row["controls"] and tutorial.unknown(row) == []


def test_a_removed_item_is_unknown():
    assert tutorial.unknown({"controls": [build.MENU[0], "removed_item"]}) == ["removed_item"]
