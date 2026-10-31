"""Regicide replay (#5032): a King in an unloaded chunk is not dead. king_check keeps the chunk of each King loaded
(forceload) before the @e check, so has_king finds it."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay_control import Clock, data  # noqa: E402


class Chunks(Clock):
    """@e finds the King k2 only when its chunk is force-loaded."""
    def __init__(self, dead=False):
        super().__init__()
        self.loaded, self.dead = False, dead

    def command(self, cmd):
        if cmd == "execute as k2 at @s run forceload add ~ ~" and not self.dead:
            self.loaded = True
        if cmd.startswith("execute if entity @e[tag=aoe2mc.p2,"):
            return "Test passed, count: 1" if self.loaded else "Test failed"
        return super().command(cmd)


def check(game):
    r = replay.Replay(game, data([]))
    r.kings = {2: {"k2"}}
    r.king_check(1000)
    return r.regicided


def test_a_king_in_an_unloaded_chunk_does_not_end_its_player():
    assert check(Chunks()) == {}


def test_a_dead_king_still_ends_its_player():
    assert check(Chunks(dead=True)) == {2: 1000}
