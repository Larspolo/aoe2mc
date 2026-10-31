"""The position-object of an AI script (#5231): up-get-point stores the tile of the target object (airef), or (-1, -1)
with no target object. The map of test_bot_gather: the villagers b0 to b4 of the bot (player 2) stand at (24, 19 + i)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses


def script():
    server, me, b = bot_map()
    me.bots = [b]
    return per.Script(per.parse(""), b), b


def run(s, text):
    """Run the actions of one rule (true) on the script."""
    for a in per.parse(f"(defrule (true) => {text})")[0].actions:
        s.act(0, a)


def at(s, goal=100):
    return s.goals[goal], s.goals[goal + 1]


def test_position_object_is_the_tile_of_the_target_object(capsys):
    s, b = script()
    run(s, "(up-find-local c: villager c: 10)")
    s.goals[100] = s.ids["b0"]
    run(s, "(up-set-target-by-id g: 100)")
    run(s, "(up-get-point position-object 100)")
    assert at(s) == (24, 19) and not capsys.readouterr().err


def test_position_object_without_a_target_is_minus_one(capsys):
    s, b = script()
    run(s, "(up-get-point position-object 100)")
    assert at(s) == (-1, -1) and not s.warned and not capsys.readouterr().err
