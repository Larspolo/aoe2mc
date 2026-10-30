"""Jump forward to a game time in a running replay (#687), with a fake clock and a fake RCON."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import build, data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402

MIL = {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "u2", "ref": 8, "tile": [3.5, 3.5]}


def timeline():
    return [{"time": 30000, "player": 1, "kind": "chat", "text": "t30000"},
            {"time": 90000, "player": 1, "kind": "move", "objects": [7], "tile": [10.5, 2.5], "names": ["VILLAGER_MALE"]},
            build(t=120000, tile=(12.0, 12.0)),
            {"time": 150000, "player": 1, "kind": "delete", "objects": [8]},
            {"time": 200000, "player": 1, "kind": "chat", "text": "t200000"},
            {"time": 400000, "player": 1, "kind": "chat", "text": "t400000"}]


def play(ai=False, jump_at=60, to=300000):
    d = data(timeline())
    d["objects"] += [VIL, MIL, HOUSE]
    game, done = Clock(), []

    def poll(control):
        if game.now >= jump_at and not done:
            control["jump"] = to
            done.append(game.now)
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll)
    return r, game


def test_a_jump_applies_the_skipped_events_without_walks():
    r, game = play()
    jump = game.sent.index("kill u2")                                   # the delete of 2:30
    assert any(c.startswith("setblock") or c.startswith("fill") for c in game.sent[:jump])   # the house of 2:00
    assert not any(c.startswith("aoe moveto") for c in game.sent)
    tps = [c for c in game.sent if c.startswith("tp u1 ")]
    assert len(tps) == 1                                                # no steps: one tp to the target
    x, _, z = map(float, tps[0].split()[2:5])
    assert math.floor(x) // 4 == 10 and math.floor(z) // 4 == 2 and not r.moving
    assert game.at == {"t30000": 30, "t400000": 160}                    # 2 skipped texts; 5:00 + 100 s at 60 s


def test_the_plugin_units_stand_at_their_target_after_a_jump():
    r, game = play(ai=True)
    moves = [c for c in game.sent if c.startswith(("aoe moveto u1", "tp u1"))]
    assert len(moves) == 2 and moves[0].split()[2:] == moves[1].split()[3:]   # tp, then an order to stay there
    x, _, z = map(float, moves[0].split()[2:5])
    assert math.floor(x) // 4 == 10 and math.floor(z) // 4 == 2


def test_a_jump_back_changes_nothing():
    _, game = play(jump_at=60, to=10000)
    assert set(game.at) == {"t30000", "t200000", "t400000"} and game.at["t400000"] == 400
