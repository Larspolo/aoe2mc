"""Live replay: a villager that dies in a fight leaves the eco view and adds no idle time (#3885)."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay import Fake  # noqa: E402
from test_replay_eco import replay_of_map, vill  # noqa: E402


class Server(Fake):
    """The entities u<k> in `live` live: counts and `execute if entity` tests answer as the server."""
    def __init__(self, live):
        super().__init__()
        self.live = set(live)

    def command(self, cmd):
        self.sent.append(cmd)
        if m := re.fullmatch(r"execute if entity (u\d+)", cmd):
            return "Test passed" if m[1] in self.live else "Test failed"
        return f"Count: {len(self.live)}" if cmd.startswith("execute if entity @e") else ""


def test_a_dead_villager_leaves_the_eco_view():
    r = replay_of_map()
    r.game = Server({"u1", "u2", "u3"})
    for k in (1, 2, 3):
        vill(r, "VILLAGER_MALE", 1, k)
    r.pop, r.troops = {1: 3}, {}
    r.census()
    r.idle_time(0)
    r.game.live.discard("u2")                                   # died in a fight: no timeline event
    r.census()
    assert r.eco()[1]["idle"] == 2
    r.idle_time(30_000)
    assert r.idled[1] == 60


def test_no_probe_while_the_count_is_the_same():
    r = replay_of_map()
    r.game = Server({"u1", "u2"})
    for k in (1, 2):
        vill(r, "VILLAGER_MALE", 1, k)
    r.pop, r.troops = {1: 2}, {}
    r.census()
    r.census()
    assert not [c for c in r.game.sent if re.fullmatch(r"execute if entity u\d+", c)]
