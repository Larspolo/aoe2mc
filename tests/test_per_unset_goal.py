"""An AI goal that the script did not set reads 0 (AoE2 DE: the goals 1 to 512 start at 0, #5824). A goal outside
1 to 512 still gives one warning."""
from test_per_bot import scripted


def ran(text):
    b = scripted(text)
    b.script.step()
    return b.script.goals


def test_an_unset_goal_reads_0_with_no_warning(capsys):
    goals = ran("(defrule (goal 100 0) => (set-goal 101 5) (disable-self))")
    assert goals == {101: 5} and capsys.readouterr().err == ""


def test_an_unset_goal_is_0_in_a_math_operand(capsys):
    goals = ran("(defrule (true) => (up-modify-goal 102 g:+ 103) (disable-self))")
    assert goals == {102: 0} and capsys.readouterr().err == ""


def test_a_goal_outside_1_to_512_still_warns(capsys):
    ran("(defrule (true) => (up-modify-goal 102 g:+ 600) (disable-self))")
    assert "goal 600" in capsys.readouterr().err
