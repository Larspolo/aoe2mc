"""The control facts and actions of AI scripts: rules, random numbers, signals, shared goals, doctrine, delete (#5047)."""
from test_per_bot import scripted
from test_per_up_shared import ally, teams


def ran(text, steps=1, **stock):
    b = scripted(text)
    b.g.stock.update(food=100, **stock)
    for _ in range(steps):
        b.script.step()
    return b


def test_disable_rule_stops_a_rule_and_enable_rule_starts_it_again():
    b = ran("""(defrule (true) => (disable-rule 1))
(defrule (true) => (set-goal 1 1))""")
    assert b.script.goals.get(1) is None
    b.script.rules[0] = ran("(defrule (true) => (enable-rule 1))").script.rules[0]
    b.script.step()
    assert b.script.goals[1] == 1


def test_random_number_is_in_range_and_seeded():
    text = "(defrule (true) => (generate-random-number 10) (disable-self)) (defrule (random-number < 11) => (set-goal 1 1))"
    one, two = ran(text).script, ran(text).script
    assert one.goals[1] == 1 and 1 <= one.random <= 10 and one.random == two.random
    assert one.fact_value("random-number", None) == one.random


def test_set_shared_goal_is_the_shared_goal_of_an_ally():
    b = scripted("(defrule (true) => (set-shared-goal 1 5) (disable-self))")
    teams(b, p2=1, p3=1)
    friend = ally(b, 3)
    b.script.step()
    assert friend.check(("shared-goal", 1, "==", 5))


def test_signals_events_and_doctrine():
    b = ran("""(defrule (true) => (set-signal 3) (set-doctrine 4) (disable-self))
(defrule (doctrine 4) => (set-goal 1 1))""")
    s = b.script
    assert s.signals[3] == 1 and s.goals[1] == 1
    s.table("event")[2] = 1
    assert s.check(("event-detected", "trigger", 2))
    s.act(0, ("acknowledge-event", "trigger", 2))
    assert not s.check(("event-detected", "trigger", 2))


def test_delete_unit_removes_one_villager():
    b = scripted("(defrule (true) => (delete-unit villager) (disable-self))")
    sent = []
    command = b.g.command
    b.g.command = lambda c: sent.append(c) or command(c)
    b.script.step()
    killed = {u for c in sent for u in b.g.villagers if c == f"execute as {u} if entity @s[tag=!aoe2mc.keep] run kill @s"}
    assert len(killed) == 1


def test_no_name_is_unknown(capsys):
    ran("""(defrule (random-number > 0) (doctrine 0) (shared-goal 1 == 0) (event-detected trigger 1) => (set-goal 1 1))
(defrule (true) => (enable-rule 0) (disable-rule 9) (generate-random-number 3) (set-signal 1) (acknowledge-event trigger 1)
(set-shared-goal 1 1) (set-doctrine 1) (delete-unit militiaman) (delete-building house) (cc-add-resource food 10))""")
    err = capsys.readouterr().err
    assert "unknown fact" not in err and "unknown action" not in err
