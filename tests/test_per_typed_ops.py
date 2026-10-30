"""Typed operators of AI scripts (c:, s:, g:, airef "Typed operators"): no exception stops the bot (#4659)."""
from test_per_bot import scripted

from game import per


def ran(text, **stock):
    b = scripted(text)
    b.g.stock.update(food=100, **stock)
    b.script.step()
    return b.script.goals


def test_c_and_s_and_g_operators_compare_with_a_constant_a_number_and_a_goal():
    sn = next(iter(per.SN))
    goals = ran(f"""(defrule (true) => (set-strategic-number {sn} 50) (set-goal 7 100) (disable-self))
(defrule (food-amount c:>= 50) => (set-goal 1 1))
(defrule (food-amount c:< 50) => (set-goal 2 1))
(defrule (food-amount s:>= {sn}) => (set-goal 3 1))
(defrule (food-amount s:> {sn}) (food-amount g:<= 7) => (set-goal 4 1))
(defrule (food-amount g:> 7) => (set-goal 5 1))""")
    assert {k for k in goals if goals[k] == 1} == {1, 3, 4}


def test_an_unknown_operator_number_or_goal_warns_once_and_is_false(capsys):
    goals = ran("""(defrule (food-amount x:> 5) => (set-goal 1 1))
(defrule (food-amount s:> sn-none) => (set-goal 2 1))
(defrule (food-amount g:> 99) => (set-goal 3 1))
(defrule (food-amount x:> 5) => (set-goal 4 1))""")
    err = capsys.readouterr().err
    assert not goals and err.count("unknown operator x:>") == 1
    assert "unknown strategic number sn-none" in err and "unknown goal 99" in err
