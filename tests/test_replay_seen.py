"""Live replay: a gather step sends its look (turn, particles, sound) only near a player, so that the replay loop keeps
up with its clock at speed 4 (#2761). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_farm import FARM, VIL, order  # noqa: E402


class Server(Fake):
    """A server with the players at `eyes` (x, y, z)."""
    def __init__(self, eyes):
        super().__init__()
        self.eyes = eyes

    def command(self, cmd):
        super().command(cmd)
        if cmd == "list":
            return f"There are {len(self.eyes)} of a max of 20 players online: " + ", ".join(
                f"p{i}" for i in range(len(self.eyes)))
        if cmd == "execute as @a run data get entity @s Pos":
            return "".join(f"p{i} has the following entity data: [{x}d, {y}d, {z}d]"
                           for i, (x, y, z) in enumerate(self.eyes))
        return ""


def play(game, end=60000):
    d = data([order(0, 40), dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, FARM]
    now = [0.0]

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, bar=True)
    return r, game.sent


def looks(sent):
    return [c for c in sent if c.split()[0] in ("rotate", "particle", "playsound") and "wheat" in c or
            c.startswith("rotate u1 ")]


@pytest.mark.parametrize("eyes, shown", [([], False), ([(200.0, 72.0, 200.0)], False), ([(28.5, 75.0, 40.2)], True),
                                         ([(200.0, 72.0, 200.0), (30.0, 71.0, 38.0)], True)])
def test_a_gather_step_shows_only_near_a_player(eyes, shown):
    r, sent = play(Server(eyes))
    assert r.eyes == eyes
    assert bool(looks(sent)) == shown
    assert r.resources(1)["food"] == play(Fake())[0].resources(1)["food"] > replay.START["food"]   # the same food without the look


def test_no_player_list_shows_each_step():
    r, sent = play(Fake())                                  # no answer: not known, as before #2761
    assert r.eyes is None and looks(sent)
