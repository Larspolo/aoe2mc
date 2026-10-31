"""The shared-goal fact with two arguments, as airef writes it: (shared-goal ID VALUE) is true when the goal holds VALUE (#5092)."""
from test_per_bot import scripted


def test_shared_goal_with_two_arguments_is_true_for_its_value_only():
    b = scripted("(defrule (true) => (up-set-shared-goal c: 31 c: 1) (disable-self))")
    b.script.step()
    assert b.script.check(("shared-goal", 31, 1))
    assert not b.script.check(("shared-goal", 31, 2))
