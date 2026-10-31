"""Live replay: a spectator that looks at a unit sees its name, player and hit points (inspect(), #5286). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

UUID = "1dcc6967-173c-2031-ccae-9650ba134730"


class Server(Fake):
    joined = frozenset({"Steve"})

    def command(self, cmd):
        self.sent.append(cmd)
        return f"{UUID} has the following entity data: 20.5f" if cmd.endswith("Health") else ""


def setup(pov=None, hidden=False):
    d = data([])
    d["objects"] = [{"kind": "unit", "name": "ARCHER", "player": 2, "tile": [6.5, 6.5], "uuid": UUID, "ref": 7}]
    r = replay.Replay(Server(), d, pov=pov)
    r.grid()
    r.units[7].pos = (26.0, 70.0, 30.0)
    if hidden:
        r.hidden = {UUID}
    return r


def facing(r, z):
    """Steve stands at (26, 70, z) and looks north (-z), at the unit when z > 30."""
    r.eye = lambda name: ((26.0, 71.62, z), (0.0, 0.0, -1.0))


def bars(cmds):
    return [c for c in cmds if " actionbar " in c]


def test_a_look_at_a_unit_shows_name_player_and_hit_points():
    r = setup()
    facing(r, 40.0)
    (c,) = bars(r.inspect(10000, clock=lambda: 0.0))
    assert c.startswith("title Steve actionbar ")
    line = "".join(lang.plain(p) for p in json.loads(c.split(" actionbar ", 1)[1]))
    hp = combat.stats("ARCHER").hp
    assert line.startswith(f"{replay.pretty('ARCHER')} (Player 2, {replay.pretty('AZTECS')}): {min(21, hp)}/{hp} | ")


def test_the_same_line_waits_then_comes_again():
    r = setup()
    facing(r, 40.0)
    assert bars(r.inspect(10000, clock=lambda: 0.0))
    assert not bars(r.inspect(10100, clock=lambda: replay.INSPECT_AGAIN - 0.1))
    assert bars(r.inspect(10200, clock=lambda: replay.INSPECT_AGAIN + 0.1))


def test_no_unit_and_a_hidden_unit_send_nothing():
    r = setup()
    facing(r, 20.0)                                                   # the unit is behind Steve
    assert not bars(r.inspect(10000, clock=lambda: 0.0))
    r = setup(pov=1, hidden=True)
    facing(r, 40.0)
    assert not bars(r.inspect(10000, clock=lambda: 0.0))


def test_an_event_line_keeps_the_bar():
    r = setup()
    facing(r, 40.0)
    r.event_bar = 10000
    assert not bars(r.inspect(11000, clock=lambda: 0.0))
    assert bars(r.inspect(10000 + replay.EVENT_BAR * 1000, clock=lambda: 0.0))
