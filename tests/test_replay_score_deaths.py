"""Live replay: the population sidebar counts down when a unit dies in a fight of the plugin (#787)."""
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_score import KNIGHT, SHEEP, sets  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


class Census(Fake):
    """A fake server: the selector count of the counted units of each player is in `alive`."""

    def __init__(self, alive):
        super().__init__()
        self.alive = alive

    def command(self, cmd):
        super().command(cmd)
        if m := re.fullmatch(rf"execute if entity @e\[tag={replay.COUNTED},tag=aoe2mc\.p(\d)\]", cmd):
            n = self.alive.get(int(m[1]), 0)
            return f"Test passed. Count: {n}" if n else "Test failed"
        return ""


def play(game, bar=True):
    d = data([dict(time=0, player=1, kind="chat", text="gl"), dict(time=3000, player=1, kind="chat", text="gg")])
    d["objects"] += [VIL, KNIGHT, SHEEP]
    now = [0.0]

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, bar=bar)
    return r


def test_a_unit_that_died_in_a_fight_counts_down():
    game = Census({1: 1})                                              # the knight of player 2 died
    r = play(game)
    assert f"tag u1 add {replay.COUNTED}" in game.sent and f"tag u2 add {replay.COUNTED}" in game.sent
    assert f"tag u3 add {replay.COUNTED}" not in game.sent             # the sheep does not count
    assert sets(c for c in game.sent if replay.POP in c) == ["P1 aoe_pop 1", "P2 aoe_pop 0"]
    assert r.pop == {1: 1, 2: 0}


def test_without_bar_no_census():
    game = Census({1: 1})
    play(game, bar=False)
    assert not any(c.startswith("execute if entity") for c in game.sent)


@pytest.mark.mc
def test_census_counts_a_killed_unit_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.forceload()
        d = data([])
        d["objects"] += [dict(VIL, uuid="00000000-0000-0000-0000-0000000000a1")]
        r = replay.Replay(game, d, ai=True)
        game.command("summon minecraft:villager 8 80 8 {UUID:[I;0,0,0,161],NoAI:1b,Tags:[\"aoe2mc.p1\"]}")
        game.command(f"tag 00000000-0000-0000-0000-0000000000a1 add {replay.COUNTED}")
        r.census()
        assert r.pop == {1: 1}
        game.command("kill 00000000-0000-0000-0000-0000000000a1")
        r.census()
        assert r.pop == {1: 0}
