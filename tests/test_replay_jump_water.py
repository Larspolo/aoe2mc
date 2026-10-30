"""A jump of the live replay while a ship sails to a water cell (#1030). Fake RCON."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_ships import DOCK, FISH, SHIP, WATER, N  # noqa: E402
from test_replay_spawn import queue  # noqa: E402
from test_replay_walk import HOUSE, VIL, Fake  # noqa: E402


@pytest.mark.parametrize("ai", [False, True])
def test_a_jump_puts_a_sailing_ship_on_the_water(ai):
    timeline = [queue(t=0, objects=[11], name="FISHING_SHIP", type=13),
                dict(time=70000, kind="move", tile=[8.5, 9.5], **SHIP),        # it sails at the jump
                dict(time=70000, player=1, kind="move", objects=[7], tile=[10.5, 2.5], names=["VILLAGER_MALE"]),
                {"time": 400000, "player": 1, "kind": "chat", "text": "end"}]
    d = data(timeline, n=N)
    d["ground"] = [" ".join("-" if (x, z) in WATER else "70" for x in range(N)) for z in range(N)]
    d["objects"] += [DOCK, FISH, HOUSE, dict(VIL, tile=[2.5, 2.5])]                # on land
    now, game, done = [0.0], Fake(), []

    def sleep(s):
        now[0] += s

    def poll(control):
        if now[0] >= 71 and not done:
            control["jump"] = 300000
            done.append(now[0])
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, poll=poll)
    assert done and not any("None" in c for c in game.sent)
    boat = r.units[900]
    tp = [c.split() for c in game.sent if c.startswith(f"tp {boat.uuid} ")]
    assert len(tp) == 1 and float(tp[0][3]) == 69                      # on the water: one block under the shore
    assert (math.floor(float(tp[0][2])), math.floor(float(tp[0][4]))) in WATER
    last = [c.split(" u1 ")[1].split() for c in game.sent if c.startswith(("tp u1 ", "aoe moveto u1 "))][-1]
    x, z = float(last[0]), float(last[2])
    assert math.floor(x) // 4 == 10 and math.floor(z) // 4 == 2          # the villager at its target, as before
