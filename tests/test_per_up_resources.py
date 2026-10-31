"""The internal resources in AI scripts: up-resource-amount, up-resource-percent, up-allied-resource-amount,
up-allied-resource-percent (#4964). The map of test_per_up_players: the bot is player 2, player 3 an ally, 4 an enemy."""

from test_per_up_players import script

from game import per, train

TEXT = """
(defrule (up-resource-amount amount-food >= {food}) => (set-goal 1 1))
(defrule (up-resource-percent food == {food100}) => (set-goal 2 1))
(defrule (up-resource-amount amount-population-cap == {cap}) => (set-goal 3 1))
(defrule (up-allied-resource-amount 3 gold == 70) => (set-goal 4 1))
(defrule (up-allied-resource-percent any-ally amount-gold > 6999) => (set-goal 5 1))
(defrule (up-allied-resource-amount 4 gold >= 0) => (set-goal 6 1))
(defrule (up-resource-amount {nosource} >= 0) => (set-goal 7 1))
"""


def test_the_four_facts_with_the_food_the_population_limit_an_ally_and_a_type_with_no_source(capsys):
    s, b, ally = script()
    ally.g.stock = {"food": 0, "wood": 0, "gold": 70, "stone": 0}
    s.stanced("any")[4].stock = dict(ally.g.stock)  # an enemy: never counts
    nosource = next(n for n, r in per.RESOURCES.items() if "source" not in r)
    food = b.g.stock["food"]
    text = TEXT.format(food=food, food100=food * 100, cap=train.limit(b.g), nosource=nosource)
    s = per.Script(per.parse(text), b)
    s.step()
    s.step()
    assert {k: s.goals.get(k) for k in range(1, 8)} == {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: None, 7: None}
    assert capsys.readouterr().err.count(f"unknown resource type {nosource}") == 1
