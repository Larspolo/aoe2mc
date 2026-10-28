"""#3281: the recap book of a person has the pages of the bots, also of a bot that the game defeated before its end
(owner feedback: "I dont see player 2's scores in the book")."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import cheats  # noqa: E402
import recap  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def setup():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    bot.share = g                                                      # a bot: bot.Bot sets it
    return server, g, bot


def titles(g):
    return [t for t, _ in recap.parts(g, lambda n: n == 1)]


def test_a_live_bot_has_its_pages():
    _, g, _ = setup()
    assert "Player 2" in titles(g) and "Player 2\n" in dict(recap.parts(g, lambda n: n == 1))["Score"]


def test_a_defeated_bot_keeps_its_pages():
    server, g, bot = setup()
    cheats.ruin(g, 2)                                                  # conquest: the bot is out of g.bots
    assert not g.bots and g.fallen_bots == [bot]
    pages = dict(recap.parts(g, lambda n: n == 1))
    assert "Player 2" in pages and "Player 2\nMilitary:" in pages["Score"]
    assert "Player 2: Defeat, score" in pages["Recap"]
    start = len(server.log)
    cheats.over(g, lambda n: n == 1)
    book = "".join(c for c in server.log[start:] if "team=p1" in c and "book" in c)
    assert "Player 2" in book and not any("team=p2" in c and "written_book" in c for c in server.log[start:])


def test_no_bot_gives_the_same_pages():
    _, g, _ = setup()
    g.bots = []
    assert titles(g) == ["Recap", "Score", "Player 1"]
