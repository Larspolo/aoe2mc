"""game/per.py: set-difficulty-parameter keeps its value with no warning (#5049). Own small script, the setup of test_per_rules."""
from test_bot_gather import bot_map

from game import per


def run(text, steps=1):
    server, me, b = bot_map()
    s = per.Script(per.parse(text), b)
    for _ in range(steps):
        s.step()
    return s, b


def test_set_difficulty_parameter_keeps_the_value_without_a_warning(capsys):
    s, b = run("(defrule (true) => (set-difficulty-parameter ability-to-dodge-missiles 0) (disable-self))")
    assert capsys.readouterr().err == ""
    assert s.difficulty == {"ability-to-dodge-missiles": 0}
