"""game/per.py: up-get-fact reads a fact given as its airef FactId number (defconst of constantsUP.per, #5808)."""
from test_bot_gather import bot_map

from game import per


def script(text):
    server, me, b = bot_map()
    return per.Script(per.parse(text), b), b


def test_fact_number_reads_the_fact(capsys):
    name = per.FACTS[min(per.FACTS)]
    s, b = script(f"(defconst my-fact {min(per.FACTS)})\n(defrule (true) => (up-get-fact my-fact 0 1))")
    b.time = 123
    s.step()
    assert s.goals[1] == s.fact_value(name, 0) and "unknown" not in capsys.readouterr().err


def test_game_time_as_number():
    s, b = script("(defconst game-time 0)\n(defrule (true) => (up-get-fact game-time 0 1))")
    b.time = 77
    s.step()
    assert s.goals[1] == 77


def test_unknown_fact_number_warns_once(capsys):
    s, b = script(f"(defrule (true) => (up-get-fact {max(per.FACTS) + 1} 0 1))")
    s.step()
    s.step()
    assert capsys.readouterr().err.count("unknown fact") == 1 and 1 not in s.goals
