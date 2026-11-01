"""Live replay: a spectator that looks at a building sees its name, player, garrison and production (#5288). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

RECT = (20, 32, 20, 32)


class Server(Fake):
    joined = frozenset({"Steve"})

    def command(self, cmd):
        self.sent.append(cmd)
        return ""


def setup():
    r = replay.Replay(Server(), data([]))
    r.grid()
    r.starts = [(9, 1, "BARRACKS", RECT)]
    r.garrisons = {RECT: [101, 102]}
    r.panels = {9: "Militia [||...]"}
    return r


def bars(cmds):
    return [c for c in cmds if " actionbar " in c]


def test_a_look_at_a_building_shows_name_player_garrison_and_production():
    r = setup()
    y = r.map.y(26, 40)
    r.eye = lambda name: ((26.0, y + 1.62, 40.0), (0.0, 0.0, -1.0))    # north, at the wall of the building
    (c,) = bars(r.inspect(10000, clock=lambda: 0.0))
    assert c.startswith("title Steve actionbar ")
    line = "".join(lang.plain(p) for p in json.loads(c.split(" actionbar ", 1)[1]))   # translate texts (#5432)
    hp = combat.stats("BARRACKS").hp
    who = r.player(1)[0]
    assert line == f"{replay.pretty('BARRACKS')} ({who}): {hp}/{hp} · garrison 2 · Militia [||...]"


def test_a_look_away_from_the_building_sends_nothing():
    r = setup()
    y = r.map.y(26, 40)
    r.eye = lambda name: ((26.0, y + 1.62, 40.0), (0.0, 0.0, 1.0))     # south: away from it
    assert not bars(r.inspect(10000, clock=lambda: 0.0))
