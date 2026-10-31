"""#5332: the sidebar of the tutorial showed Wood -180 and Food -220. tutorial.give added the resources of a step to
the stock but not to the board, so each later payment (build.found, train.queue: both remove from the stock and the
board) took the board below the stock and below zero."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import tutorial  # noqa: E402

GIVES = [row for row in tutorial.STEPS if "give" in row]


class Game:
    """The stock and the board of one player: the board follows the scoreboard commands, as the sidebar does."""
    board = "aoe_res"

    def __init__(self):
        self.stock = {r: 0 for row in GIVES for r in row["give"]}
        self.shown = dict.fromkeys(self.stock, 0)

    def command(self, cmd):
        m = re.fullmatch(r"scoreboard players (add|remove|set) (\w+) aoe_res (-?\d+)", cmd)
        if m:
            op, r, v = m[1], m[2].lower(), int(m[3])
            self.shown[r] = v if op == "set" else self.shown[r] + (v if op == "add" else -v)
        return ""

    def pay(self, cost):
        """A payment as build.found and train.queue make it."""
        for r, v in cost.items():
            self.stock[r] -= v
            self.command(f"scoreboard players remove {r.capitalize()} {self.board} {v}")


def test_tutorial_has_steps_that_give():
    assert GIVES


def test_give_shows_the_resources_on_the_board():
    g = Game()
    for row in GIVES:
        tutorial.give(g, row)
        assert g.shown == g.stock


def test_payment_of_the_given_resources_never_shows_a_negative_amount():
    g = Game()
    for row in GIVES:
        tutorial.give(g, row)
        g.pay(row["give"])                                             # the step spends what it gave
        assert g.shown == g.stock
        assert min(g.shown.values()) >= 0
