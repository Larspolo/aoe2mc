"""Goals by reference and goal flags of AI scripts (up-get-indirect-goal, up-set-indirect-goal, up-modify-flag,
up-compare-flag, airef "typeOp"): the c: and g: prefixes, one warning for another operator (#4865)."""
from test_per_bot import scripted


def ran(text, **stock):
    b = scripted(text)
    b.g.stock.update(food=100, **stock)
    b.script.step()
    return b.script.goals


def test_up_get_indirect_goal_reads_the_goal_whose_id_is_the_constant_or_a_goal():
    goals = ran("""(defrule (true) => (set-goal 5 9) (set-goal 7 8) (set-goal 2 7)
(up-get-indirect-goal c: 5 1) (up-get-indirect-goal g: 2 3) (disable-self))""")
    assert goals[1] == 9 and goals[3] == 8                             # c: 5 is goal 5; g: 2 holds the id 7


def test_up_set_indirect_goal_sets_the_goal_whose_id_is_the_constant_or_a_goal():
    goals = ran("""(defrule (true) => (set-goal 5 9) (set-goal 7 8) (set-goal 2 7) (set-goal 4 3)
(up-set-indirect-goal c: 5 c: 1) (up-set-indirect-goal g: 2 g: 4) (up-set-indirect-goal c: 5 g: 4) (disable-self))""")
    assert goals[5] == 3 and goals[7] == 3                             # the third command sets goal 5 to goal 4


def test_up_modify_flag_sets_and_clears_the_bits_with_the_c_and_g_prefixes():
    goals = ran("""(defrule (true) => (set-goal 1 1) (set-goal 9 4) (set-goal 8 2)
(up-modify-flag 1 c:+ 2) (up-modify-flag 1 g:+ 9) (up-modify-flag 1 c:- 1) (up-modify-flag 1 g:- 8) (disable-self))""")
    assert goals[1] == 4                                               # 1 | 2 | 4, then the bits 1 and 2 are removed


def test_up_compare_flag_is_true_when_all_bits_are_in_the_goal_with_the_c_and_g_prefixes():
    goals = ran("""(defrule (true) => (set-goal 1 5) (set-goal 9 4) (set-goal 2 0))
(defrule (up-compare-flag 1 c:== 4) => (set-goal 11 1))
(defrule (up-compare-flag 1 c:== 6) => (set-goal 12 1))
(defrule (up-compare-flag 1 c:!= 6) => (set-goal 13 1))
(defrule (up-compare-flag 1 g:== 9) => (set-goal 14 1))
(defrule (up-compare-flag 1 g:!= 9) => (set-goal 15 1))
(defrule (up-compare-flag 2 c:!= 4) => (set-goal 16 1))""")
    assert {k for k in goals if goals[k] == 1} == {11, 13, 14, 16}


def test_up_modify_flag_with_another_operator_warns_once_and_keeps_the_goal(capsys):
    goals = ran("""(defrule (true) => (set-goal 1 5) (up-modify-flag 1 c:* 2) (up-modify-flag 1 c:* 2) (disable-self))""")
    err = capsys.readouterr().err
    assert goals[1] == 5 and err.count("unknown operator c:*") == 1
