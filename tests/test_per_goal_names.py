"""A goal stores the number of a name constant (#5181): with-escrow, without-escrow, a unit; up-can-train and
up-train then read it with no exception."""
import per
from test_per_bot import scripted


def ran(text):
    b = scripted(text)
    b.g.stock.update(food=100)
    b.script.step()
    return b.script.goals


def test_set_goal_stores_the_id_of_a_name():
    goals = ran("""(defrule (true) => (set-goal 1 with-escrow) (set-goal 2 without-escrow) (set-goal 3 militiaman)
(up-modify-goal 4 c:= with-escrow) (disable-self))""")
    ids = {k: per.names()[k]["id"] for k in ("with-escrow", "without-escrow", "militiaman")}
    assert goals == {1: ids["with-escrow"], 2: ids["without-escrow"], 3: ids["militiaman"], 4: ids["with-escrow"]}


def test_a_name_with_no_id_is_0_with_one_warning(capsys):
    goals = ran("(defrule (true) => (set-goal 1 no-such-name) (set-goal 2 no-such-name) (disable-self))")
    assert goals == {1: 0, 2: 0} and capsys.readouterr().err.count("no-such-name") == 1


def test_up_can_train_and_up_train_read_an_escrow_goal():
    ran("""(defrule (true) => (set-goal 1 with-escrow) (disable-self))
(defrule (up-can-train 1 c: spearman-line) => (up-train 1 c: spearman-line))""")
