"""game/per.py: Script runs the rules of an AI script on a bot (#4528). Own small scripts, the map of test_bot_gather."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # the modules that per uses


def run(text, steps=1, **stock):
    server, me, b = bot_map()
    b.g.stock.update(stock)
    s = per.Script(per.parse(text), b)
    for _ in range(steps):
        s.step()
    return s, b, server


def queued(b):
    return [e["name"] for q in b.g.queues.values() for e in q]


def test_train_a_villager_when_the_facts_are_true():
    price = train.price(bot_map()[2].g, "VILLAGER_MALE")["food"]
    s, b, _ = run("(defrule (food-amount >= 50) (can-train villager) => (train villager))", food=price)
    assert queued(b) == ["VILLAGER_MALE"]
    s, b, _ = run("(defrule (food-amount >= 50) (can-train villager) => (train villager))", food=price - 1)
    assert queued(b) == []                                             # can-train needs the cost


def test_disable_self_stops_the_rule_after_its_first_run():
    s, b, _ = run("(defrule (true) => (train villager) (disable-self))", steps=3, food=1000)
    assert queued(b) == ["VILLAGER_MALE"]


def test_research_and_research_completed():
    s, b, _ = run("(defrule (can-research ri-loom) => (research ri-loom))", steps=2, gold=1000)
    assert queued(b) == ["LOOM"]                                       # can-research is false when it is queued
    b.g.techs.add("LOOM")
    assert s.check(("research-completed", "ri-loom")) and not s.check(("can-research", "ri-loom"))


def test_build_a_house():
    wood = build.price(bot_map()[2].g, "HOUSE")["wood"]
    s, b, _ = run("(defrule (can-build house) (building-type-count house == 0) => (build house) (disable-self))",
                  steps=2, wood=wood)
    assert [x["name"] for x in b.g.sites] == ["HOUSE"] and b.g.stock["wood"] == 0


def test_facts_of_the_state():
    s, b, _ = run("", food=10, wood=20, gold=30, stone=40)
    b.g.pop, b.time = 3, 120
    yes = [("food-amount", "==", 10), ("wood-amount", ">", 19), ("gold-amount", "<", 31), ("stone-amount", "<=", 40),
           ("game-time", ">=", 120), ("population", "==", 3), ("civilian-population", "==", len(b.g.villagers)),
           ("military-population", "==", len(b.g.soldiers)), ("housing-headroom", "==", train.limit(b.g) - 3),
           ("population-headroom", "==", train.max_pop(b.g) - 3), ("current-age", "==", "dark-age"),
           ("unit-type-count", "villager", "==", len(b.g.villagers)), ("building-type-count", "town-center", "==", 1),
           ("not", ("false",)), ("or", ("false",), ("true",)), ("nor", ("false",), ("false",)),
           ("nand", ("true",), ("false",)), ("and", ("true",), ("true",))]
    assert [f for f in yes if not s.check(f)] == []
    b.g.techs.add(build.AGE_TECHS[0])
    assert s.check(("current-age", ">=", "feudal-age")) and not s.check(("current-age", "==", "dark-age"))


def test_goals_and_timers_keep_their_values_between_steps():
    s, b, _ = run("""
(defrule (true) => (set-goal 1 5) (enable-timer 2 60) (disable-self))
(defrule (goal 1 5) (timer-triggered 2) => (set-goal 3 1) (disable-timer 2))
""")
    assert s.goals == {1: 5} and s.timers == {2: 60}
    b.time = 59
    s.step()
    assert 3 not in s.goals
    b.time = 60
    s.step()
    assert s.goals[3] == 1 and s.timers == {}
    assert s.check(("goal", 1, ">", 4))


def test_chat_and_do_nothing():
    s, b, server = run('(defrule (true) => (do-nothing) (chat-to-all "Hello") (disable-self))')
    assert any("tellraw" in c and "Hello" in c for c in server.log)


def test_an_unknown_name_warns_once_and_the_other_rules_run(capsys):
    s, b, _ = run("""
(defrule (moon-phase == 3) => (set-goal 1 1))
(defrule (true) => (dance) (build no-such-building) (set-goal 2 1))
""", steps=3)
    err = capsys.readouterr().err
    assert s.goals == {2: 1}
    assert err.count("moon-phase") == 1 and err.count("dance") == 1 and err.count("no-such-building") == 1
