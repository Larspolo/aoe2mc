"""#3039: a trained scout whose first order is AUTOSCOUT gets its unit at that order and walks (Fake RCON, ai=True).
The scout trains 30 s: the order comes after the spawn at 30 s."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_spawn import TC, queue  # noqa: E402


def test_a_trained_scout_explores_at_its_first_autoscout_order():
    tl = [queue(t=0, name="SCOUT_CAVALRY", type=448),
          dict(time=31000, player=1, kind="autoscout", objects=[40], names=["SCOUT_CAVALRY"]),
          dict(time=61000, player=1, kind="chat", text="end")]
    d = data(tl)
    d["objects"].append(TC)
    now, game = [0.0], Fake()
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None)
    assert 40 in r.units and 40 in r.scouts
    assert any(c.startswith(f"aoe moveto {r.units[40].uuid} ") for c in game.sent)   # the walk of the plugin
