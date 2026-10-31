"""The airef argument forms of up-add-object-cost and up-add-research-cost (#5180): typeOp, name, typeOp, value."""
from test_per_bot import scripted

from game import per, train


def run(text, **stock):
    b = scripted(text)
    b.g.stock.update({"food": 100, "wood": 100, "stone": 100, "gold": 100, **stock})
    b.script.step()
    return b


def goals_of(b, first):
    return [b.script.goals.get(first + i) for i in range(len(per.COST_GOODS))]


def price(b, game_name):
    cost = train.price(b.g, game_name)
    return [cost.get(r, 0) for r in per.COST_GOODS]


def test_up_add_object_cost_reads_the_airef_order_for_a_unit():
    b = run("""(defrule (true) => (up-setup-cost-data 1 10))
(defrule (true) => (up-add-object-cost c: spearman c: 4))""")
    assert goals_of(b, 10) == [4 * v for v in price(b, "SPEARMAN")]


def test_up_add_object_cost_takes_the_value_from_a_goal():
    b = run("""(defrule (true) => (set-goal 5 3) (up-setup-cost-data 1 10))
(defrule (true) => (up-add-object-cost c: spearman g: 5))""")
    assert goals_of(b, 10) == [3 * v for v in price(b, "SPEARMAN")]


def test_up_add_object_cost_of_a_line_adds_the_unit_it_can_train_now():
    b = run("""(defrule (true) => (up-setup-cost-data 1 10))
(defrule (true) => (up-add-object-cost c: archer-line c: 1))""")
    unit = next(u for u in reversed(train.forms("ARCHER")) if train.unlocked(b.g, u))
    assert goals_of(b, 10) == price(b, unit)


def test_up_add_research_cost_reads_the_airef_order_for_a_technology():
    b = run("""(defrule (true) => (up-setup-cost-data 1 10))
(defrule (true) => (up-add-research-cost c: ri-loom c: -1))""")
    assert goals_of(b, 10) == [-v for v in price(b, "LOOM")]
