"""Live replay: the military line of each player in the summary at the end (#1066): military units trained, units
lost, buildings lost. Fake RCON and a fake clock."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402
from test_replay_spawn import queue  # noqa: E402
from test_replay_summary import HEAD, play  # noqa: E402


def military(sent):
    """The military lines after the summary header."""
    rest = sent[sent.index(HEAD) + 1:]
    return ["".join(t["text"] for t in json.loads(c.split(" ", 2)[2])) for c in rest
            if c.startswith("tellraw @a [") and "military" in c]


def test_the_end_shows_the_military_of_each_player():
    tl = [queue(t=0), queue(t=1000, name="ARCHER", type=4), queue(t=2000, name="ARCHER", type=4),
          delete(100_000, [7]), delete(101_000, [8], player=2), delete(102_000, [5]),     # villager, knight, TC
          dict(time=120_000, player=1, kind="chat", text="gg")]
    r, sent = play(tl)
    assert (r.army, r.lost, r.razed) == ({1: 2}, {1: 1, 2: 1}, {1: 1})
    lines = military(sent)
    assert "Player 1 (Britons): military units trained 2, units lost 1, buildings lost 1, APM 2" in lines
    assert "Player 2 (Aztecs): military units trained 0, units lost 1, buildings lost 0, APM 0" in lines


def test_a_census_counts_the_units_that_died_in_a_fight():
    class Census(Fake):
        count = {1: 5, 2: 3}

        def command(self, cmd):
            super().command(cmd)
            p = int(cmd.rsplit("aoe2mc.p", 1)[1][0]) if cmd.startswith("execute if entity") else None
            return f"Test passed, Count: {self.count[p]}" if p else ""
    game = Census()
    r = replay.Replay(game, data([]))
    r.pop = {1: 6, 2: 3}
    r.census()                                                          # the first census: a start unit has no entity
    assert r.pop == {1: 5, 2: 3} and r.lost == {}
    game.count = {1: 3, 2: 3}
    r.census()
    assert r.pop == {1: 3, 2: 3} and r.lost == {1: 2}
