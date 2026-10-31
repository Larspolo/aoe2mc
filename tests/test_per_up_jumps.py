"""UserPatch jumps of AI scripts (up-jump-rule, up-jump-direct, up-jump-dynamic, up-get-rule-id, #4866)."""
from test_per_bot import scripted


def ran(text, **stock):
    b = scripted(text)
    b.g.stock.update(food=100, **stock)
    b.script.step()
    return b.script


def test_up_jump_rule_skips_the_next_rule():
    goals = ran("""(defrule (true) => (set-goal 1 1) (up-jump-rule 1))
(defrule (true) => (set-goal 2 1))
(defrule (true) => (set-goal 3 1))""").goals
    assert goals == {1: 1, 3: 1}


def test_up_jump_rule_minus_one_runs_the_rule_again_three_times():
    goals = ran("""(defrule (true) => (set-goal 1 0))
(defrule (up-compare-goal 1 c:< 3) => (up-modify-goal 1 c:+ 1) (up-jump-rule -1))
(defrule (true) => (set-goal 2 1))""").goals
    assert goals == {1: 3, 2: 1}


def test_up_jump_direct_goes_to_the_rule_that_up_get_rule_id_stored():
    goals = ran("""(defrule (true) => (up-get-rule-id 4) (up-modify-goal 4 c:+ 3) (up-jump-direct g: 4))
(defrule (true) => (set-goal 8 1))
(defrule (true) => (set-goal 9 1))
(defrule (true) => (set-goal 10 1))""").goals
    assert goals == {4: 3, 10: 1}


def test_up_jump_dynamic_goes_from_the_rule_by_the_delta():
    goals = ran("""(defrule (true) => (up-jump-dynamic c: 2))
(defrule (true) => (set-goal 8 1))
(defrule (true) => (set-goal 9 1))
(defrule (true) => (set-goal 10 1))""").goals
    assert goals == {10: 1}


def test_a_loop_with_no_end_stops_with_one_warning_and_the_next_step_runs_again(capsys):
    script = ran("""(defrule (true) => (up-modify-goal 1 c:+ 1))
(defrule (true) => (up-jump-rule -1))""")
    script.step()
    assert script.goals[1] == 1                                        # one rule run per step: -1 + 1, then + 1
    err = capsys.readouterr().err
    assert err.count("a loop of rules has no end") == 1
