"""#3111: the board (the scoreboard objective of the resources) of each side holds the resources of the mode of
Defend the Wonder, as its stock does. Fake server of test_gather, a replay of the scoreboard commands."""
import re

from test_defend_wonder_walls import game, players

from game import gather


def replay(log):
    """The scores of the scoreboard commands of log: {(objective, holder): value}."""
    scores = {}
    for cmd in log:
        if m := re.fullmatch(r"scoreboard players (set|add|remove) (\S+) (\S+) (\d+)", cmd):
            key, n = (m[3], m[2]), int(m[4])
            scores[key] = n if m[1] == "set" else scores.get(key, 0) + (n if m[1] == "add" else -n)
    return scores


def test_the_board_of_each_side_holds_the_stock_of_the_mode():
    for n, h in players(game()).items():
        scores = replay(h.game.log)
        for r in gather.RESOURCES:
            assert scores[(h.board, r)] == h.stock[r.lower()], (n, r)
