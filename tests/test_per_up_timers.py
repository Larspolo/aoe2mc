"""The timer commands of AI scripts: up-timer-status, up-set-timer and up-get-timer (#4867)."""
from test_per_bot import scripted


def ran(text, t):
    b = scripted(text)
    b.g.stock.update(food=100)
    b.time = t
    b.script.step()
    return b.script.goals


def test_up_timer_status_reads_the_disabled_running_and_triggered_states():
    text = """(defrule (true) => (up-set-timer "" 5 "" 60) (disable-self))
(defrule (up-timer-status 5 == timer-running) => (set-goal 1 1))
(defrule (up-timer-status 5 == timer-triggered) => (set-goal 2 1))
(defrule (up-timer-status 5 == timer-disabled) => (set-goal 3 1))"""
    b = scripted(text)
    b.g.stock.update(food=100)
    b.time = 0
    b.script.step()
    assert {k for k, v in b.script.goals.items() if v == 1} == {1}     # set at 0, due at 60: running
    b.time = 60
    b.script.step()
    assert {k for k, v in b.script.goals.items() if v == 1} == {1, 2}  # due: triggered
    assert 3 not in b.script.goals


def test_up_timer_status_is_disabled_for_a_timer_never_set():
    goals = ran("(defrule (up-timer-status 5 == timer-disabled) => (set-goal 1 1))", 0)
    assert goals == {1: 1}


def test_up_set_timer_with_minus_one_disables_the_timer():
    text = """(defrule (true) => (up-set-timer "" 5 "" 60) (up-set-timer "" 5 "" -1) (disable-self))
(defrule (up-timer-status 5 == timer-disabled) => (set-goal 1 1))"""
    goals = ran(text, 0)
    assert goals == {1: 1}


def test_up_get_timer_gives_the_due_time_in_milliseconds_or_zero_when_disabled():
    text = """(defrule (true) => (up-set-timer "" 5 "" 60) (up-get-timer "" 5 7) (up-get-timer "" 6 8) (disable-self))"""
    goals = ran(text, 30)
    assert goals[7] == 90000                                           # set at 30 s for 60 s: due at 90 s
    assert goals[8] == 0                                               # timer 6 is disabled
