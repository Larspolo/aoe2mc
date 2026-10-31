"""The victory and treaty data of AI scripts: up-get-victory-data, up-get-victory-limit, up-get-treaty-data (#4873)."""
import types

import per
from test_per_bot import scripted

TEXT = "(defrule (true) => (up-get-victory-data 1 2 3) (up-get-victory-limit 4) (up-get-treaty-data 5) (disable-self))"


def ran(**g):
    b = scripted(TEXT)
    vars(b.g).update(g)
    b.script.step()
    return b.script.goals


def test_a_wonder_in_progress_a_time_limit_and_no_treaty():
    goals = ran(victory="time-limit", victory_value=300, wonders={7: dict(player=2, left=99.5)},
                game=types.SimpleNamespace(treaty=0.0, treaty_time=0.0))
    assert goals == {1: 2, 2: per.VICTORY_TYPES["time-limit"], 3: 100, 4: 300, 5: 0}


def test_the_relic_timer_that_ends_first_and_the_treaty_left():
    goals = ran(victory="standard", wonders={7: dict(player=2, left=300.0)}, relic_timer=dict(player=3, left=50.0),
                game=types.SimpleNamespace(treaty=600.0, treaty_time=100.0))
    assert (goals[1], goals[3], goals[4], goals[5]) == (3, 50, 0, 500)


def test_no_timer_gives_zero():
    goals = ran(victory="conquest")
    assert (goals[1], goals[3], goals[5]) == (0, 0, 0)
