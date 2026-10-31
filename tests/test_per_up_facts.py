"""game/per.py: up-get-fact, up-get-player-fact and up-get-fact-min, -max, -sum store the value of a fact in a goal
(#4868). The map of test_bot_gather: player 1 (a person) and the bot, player 2, and a second bot, player 3; all are
enemies (no team)."""
from test_bot_gather import bot_map

from game import bot, per
from game.bot import build, train  # noqa: F401  (the modules that per uses)


def script(text=""):
    server, me, b = bot_map()
    other = bot.Bot(server, me.data, player=3, share=me).setup()
    me.bots = [b, other]                                               # run.py: player 1 holds the bots
    return per.Script(per.parse(text), b), b, me, other.g


def test_up_get_fact_of_a_resource_a_population_and_a_count():
    s, b, me, third = script("(defrule (true) => (up-get-fact wood-amount 0 1) (up-get-fact military-population 0 2)"
                             " (up-get-fact building-type-count town-center 3) (up-get-fact population-cap 0 4))")
    b.g.stock["wood"] = 123
    b.g.soldiers.update({"s0": "MILITIA", "s1": "MILITIA"})
    s.step()
    assert s.goals[1] == 123 and s.goals[2] == 2 and s.goals[3] == 1 and s.goals[4] == train.limit(b.g)


def test_a_fact_form_is_true_and_runs():
    s, b, me, third = script("(defrule (up-get-fact military-population 0 5) => (set-goal 6 1))")
    s.step()
    assert s.goals == {5: 0, 6: 1}


def test_player_facts_and_min_max_sum_over_two_enemies():
    s, b, me, third = script()
    me.soldiers.update({f"m{i}": "MILITIA" for i in range(3)})
    third.soldiers.update({f"t{i}": "MILITIA" for i in range(5)})
    focus = len(s.sides("focus-player")[0][0].soldiers)
    for form, goal in ((("up-get-player-fact", 3, "military-population", 0, 1), 5),
                       (("up-get-player-fact", "focus-player", "military-population", 0, 1), focus),
                       (("up-get-fact-min", "any-enemy", "military-population", 0, 1), 3),
                       (("up-get-fact-max", "any-enemy", "military-population", 0, 1), 5),
                       (("up-get-fact-sum", "any-enemy", "military-population", 0, 1), 8)):
        assert s.check(form) and s.goals[1] == goal, form


def test_an_unknown_fact_warns_once_and_the_next_rules_run(capsys):
    s, b, me, third = script("(defrule (true) => (up-get-fact no-such-fact 0 1) (set-goal 2 1))\n"
                             "(defrule (true) => (set-goal 3 1))")
    s.step()
    s.step()
    assert 1 not in s.goals and s.goals[2] == 1 and s.goals[3] == 1
    assert capsys.readouterr().err.count("no-such-fact") == 1
