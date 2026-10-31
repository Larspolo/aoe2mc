"""The cost data of AI scripts: up-setup-cost-data, up-reset-cost-data, up-add-cost-data, up-add-object-cost,
up-add-research-cost and up-get-cost-delta (#4879). A cost set is 4 goals in a row: food, wood, stone, gold."""
from test_per_bot import scripted

from game import per, train


def run(text, **stock):
    b = scripted(text)
    b.g.stock.update({"food": 100, "wood": 100, "stone": 100, "gold": 100, **stock})
    b.script.step()
    return b


def goals_of(b, first):
    return [b.script.goals.get(first + i) for i in range(len(per.COST_GOODS))]


def price(b, script_name):
    """The AoE2 cost of a script name, in the order of the cost set (COST_GOODS)."""
    cost = train.price(b.g, per.names()[script_name]["game"])
    return [cost.get(r, 0) for r in per.COST_GOODS]


def test_up_setup_cost_data_keeps_the_goals_or_resets_them():
    kept = run("""(defrule (true) => (set-goal 1 5) (set-goal 2 6) (set-goal 3 7) (set-goal 4 8))
(defrule (true) => (up-setup-cost-data 0 1))""")
    assert goals_of(kept, 1) == [5, 6, 7, 8]
    reset = run("""(defrule (true) => (set-goal 1 5) (set-goal 2 6) (set-goal 3 7) (set-goal 4 8))
(defrule (true) => (up-setup-cost-data 1 1))""")
    assert goals_of(reset, 1) == [0, 0, 0, 0]


def test_up_reset_cost_data_sets_its_four_goals_to_zero():
    b = run("""(defrule (true) => (set-goal 20 5) (set-goal 21 6) (set-goal 22 7) (set-goal 23 8) (set-goal 24 9))
(defrule (true) => (up-reset-cost-data 20))""")
    assert goals_of(b, 20) == [0, 0, 0, 0]
    assert b.script.goals[24] == 9


def test_up_add_object_cost_adds_the_cost_of_a_unit_times_the_value():
    b = run("""(defrule (true) => (up-setup-cost-data 1 10))
(defrule (true) => (up-add-object-cost c: archer c: 2))""")
    assert goals_of(b, 10) == [2 * v for v in price(b, "archer")]


def test_up_add_research_cost_subtracts_the_cost_of_a_technology_for_a_negative_value():
    b = run("""(defrule (true) => (up-setup-cost-data 1 10))
(defrule (true) => (up-add-research-cost c: ri-architecture c: -1))""")
    assert goals_of(b, 10) == [-v for v in price(b, "ri-architecture")]


def test_up_add_cost_data_adds_the_set_at_a_goal_times_the_value():
    b = run("""(defrule (true) => (set-goal 30 1) (set-goal 31 2) (set-goal 32 3) (set-goal 33 4))
(defrule (true) => (up-setup-cost-data 1 10))
(defrule (true) => (up-add-cost-data 30 c 3))""")
    assert goals_of(b, 10) == [3, 6, 9, 12]
    assert goals_of(b, 30) == [1, 2, 3, 4]


def test_up_get_cost_delta_puts_the_stock_minus_the_set_into_four_goals():
    b = run("""(defrule (true) => (set-goal 10 1) (set-goal 11 2) (set-goal 12 3) (set-goal 13 4))
(defrule (true) => (up-setup-cost-data 0 10))
(defrule (true) => (up-get-cost-delta 40))""", food=50, wood=60, stone=70, gold=80)
    assert goals_of(b, 40) == [49, 58, 67, 76]


def test_the_cost_actions_that_add_need_a_set_first(capsys):
    b = run("""(defrule (true) => (set-goal 40 9))
(defrule (true) => (up-add-object-cost c: archer c: 2))
(defrule (true) => (up-get-cost-delta 40))""")
    assert goals_of(b, 40) == [9, None, None, None]
    assert "cost data" in capsys.readouterr().err
