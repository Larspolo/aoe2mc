"""The campaign titles go to the players after their join, not to an empty server (#3772)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402
from test_start_on_join import FakeGame, Side, join_after  # noqa: E402


def test_title_after_the_join():
    game, now = FakeGame(), [0.0]
    game.titles = ("The Campaign", "Scenario 1: Start")
    sleep = join_after(game, ["Steve"], now)
    run.start_on_join(game, [Side(lambda: now[0])], 1, sleep=lambda s: (game.command("sleep"), sleep(s)))
    assert game.sent[:3] == ["sleep", "scoreboard players reset #wait aoe_trig", "tick unfreeze"]
    assert game.sent[3:] == ['title @a subtitle "Scenario 1: Start"', 'title @a title "The Campaign"']


def test_no_titles_no_command():
    game = FakeGame()
    run.show_titles(game)
    assert game.sent == []
