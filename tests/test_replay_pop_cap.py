"""Live replay: no unit trains at the population cap of 200; it trains after a death (#4626). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_spawn import TC, queue, summons  # noqa: E402


class Server(Fake):
    """A census counts `live` units."""
    def __init__(self):
        super().__init__()
        self.live = 0

    def command(self, cmd):
        self.sent.append(cmd)
        return f"Count: {self.live}" if cmd.startswith("execute if entity @e") else ""


def test_a_queue_at_the_cap_waits_for_a_death():
    d = data([queue()])
    d["objects"].append(TC)
    r = replay.Replay(Server(), d, ai=True)
    e, = r.spawns()
    r.pop[1] = replay.POP_LIMIT
    assert summons(r.commands(e)) == [] and r.pop[1] == replay.POP_LIMIT
    r.game.live = replay.POP_LIMIT - 1                         # a unit died in a fight
    r.game.sent.clear()
    r.census(e["time"] + 5000)
    r.flush()
    assert len(summons(r.game.sent)) == 1 and r.pop[1] == replay.POP_LIMIT


def test_a_queue_below_the_cap_trains():
    d = data([queue()])
    d["objects"].append(TC)
    r = replay.Replay(Fake(), d)
    e, = r.spawns()
    r.pop[1] = replay.POP_LIMIT - 1
    assert len(summons(r.commands(e))) == 1
