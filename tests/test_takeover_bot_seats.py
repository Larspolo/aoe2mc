"""--takeover 1 with --bots all: no bot plays player 1, the player of the person (#5624)."""
from game import run

PLAYERS = {"1": {}, "2": {}}


def seats(people):
    """The bot seats of play(): the takeover seats, else the seats after one person."""
    taken = run.takeover_seats(PLAYERS, people)
    return taken if taken is not None else run.bot_seats(PLAYERS, 1, "all")


def test_takeover_1_bot_plays_only_player_2():
    assert [p for p, _ in seats(())] == [2]


def test_takeover_2_bot_plays_only_player_1():
    assert [p for p, _ in seats((2,))] == [1]
