"""UserPatch commands with goals and strategic numbers of AI scripts (up-modify-goal, up-modify-sn, up-compare-*, #4862)."""
import pytest
from test_per_bot import scripted

from game import per


def ran(text, **stock):
    b = scripted(text)
    b.g.stock.update(food=100, **stock)
    b.script.step()
    return b.script


# (operator, value, ref, the new value): ref 2, except % (10 %* 29 = 2) and %/ (7 %/ 9 = 77)
CASES = [("=", 7, 2, 2), ("+", 7, 2, 9), ("-", 7, 2, 5), ("*", 7, 2, 14), ("/", 7, 2, 4), ("z/", 7, 2, 3),
         ("mod", 7, 2, 1), ("min", 7, 2, 2), ("max", 7, 2, 7), ("neg", 7, 2, -2), ("%*", 10, 29, 2), ("%/", 7, 9, 77)]


@pytest.mark.parametrize("op, value, ref, want", CASES)
def test_up_modify_goal_does_each_math_operator_with_each_prefix(op, value, ref, want):
    sn = next(iter(per.SN))
    for prefix, arg in (("c:", ref), ("g:", 2), ("s:", sn)):          # the operand: a constant, goal 2, or the number sn
        script = ran(f"""(defrule (true) => (set-goal 1 {value}) (set-goal 2 {ref}) (set-strategic-number {sn} {ref})
(up-modify-goal 1 {prefix}{op} {arg}) (disable-self))""")
        assert script.goals[1] == want, prefix


def test_up_modify_sn_does_a_math_operator():
    sn = next(iter(per.SN))
    script = ran(f"""(defrule (true) => (set-strategic-number {sn} 10) (up-modify-sn {sn} c:+ 3) (disable-self))""")
    assert script.sn[sn] == 13


def test_up_modify_goal_as_a_fact_changes_the_goal_and_is_true():
    script = ran("""(defrule (true) => (set-goal 1 7))
(defrule (up-modify-goal 1 c:+ 3) => (set-goal 2 1))""")
    assert script.goals == {1: 10, 2: 1}


def test_up_compare_facts_read_goals_strategic_numbers_and_constants():
    sn = next(iter(per.SN))
    goals = ran(f"""(defrule (true) => (set-goal 2 4) (set-goal 5 9) (set-strategic-number {sn} 4))
(defrule (up-compare-goal 2 c:== 4) => (set-goal 11 1))
(defrule (up-compare-goal 2 g:< 5) => (set-goal 12 1))
(defrule (up-compare-goal 2 s:== {sn}) => (set-goal 13 1))
(defrule (up-compare-goal 2 g:> 5) => (set-goal 14 1))
(defrule (up-compare-sn {sn} c:>= 4) => (set-goal 15 1))
(defrule (up-compare-sn {sn} g:> 5) => (set-goal 16 1))
(defrule (up-compare-sn {sn} s:== {sn}) => (set-goal 17 1))
(defrule (up-compare-const 4 c:== 4) => (set-goal 18 1))
(defrule (up-compare-const 4 s:< {sn}) => (set-goal 19 1))
(defrule (up-compare-const 4 g:< 5) => (set-goal 20 1))""").goals
    assert {k for k in goals if goals[k] == 1} == {11, 12, 13, 15, 17, 18, 20}


def test_an_unknown_math_operator_warns_once_and_the_next_rules_run(capsys):
    goals = ran("""(defrule (true) => (set-goal 1 5) (up-modify-goal 1 x:+ 3))
(defrule (true) => (set-goal 3 1))
(defrule (true) => (up-modify-goal 1 x:+ 3))""").goals
    assert goals == {1: 5, 3: 1}
    assert capsys.readouterr().err.count("unknown operator x:+") == 1


def test_a_division_by_zero_keeps_the_value():
    goals = ran("""(defrule (true) => (set-goal 1 7) (up-modify-goal 1 c:/ 0) (up-modify-goal 1 c:mod 0)
(up-modify-goal 1 c:%/ 0) (disable-self))""").goals
    assert goals == {1: 7}
