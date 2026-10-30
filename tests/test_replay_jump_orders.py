"""#2734: a jump of the live replay keeps the stance, patrol, attack-move and other orders of the skipped time, as the
play without a jump. Fake RCON on Paper."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def jump(timeline, to=60000):
    d = data(timeline)
    d["objects"] += [VIL, MIL]
    r = replay.Replay(Fake(), d, ai=True)
    return r, r.jump(d["timeline"], to)


def ev(t, kind, **k):
    return dict(time=t, player=1, kind=kind, objects=[8], names=["MILITIA"], **k)


def test_a_stance_of_the_skipped_time_is_set():
    r, sent = jump([ev(1000, "stance", stance="Defensive")])
    assert "aoe stance u2 defensive" in sent and r.stances == {8: "defensive"}


def test_a_patrol_of_the_skipped_time_goes_on():
    r, sent = jump([ev(1000, "patrol", tile=[10.5, 10.5])])
    assert r.patrols[8][0] == [[3.5, 10.5], [10.5, 10.5]]
    assert "tp u2 42.5 70.0 42.5" in sent                         # it stands at the patrol tile, no walk there
    assert sent[-1].startswith("aoe moveto u2 ")                  # then it walks back, as in play


def test_an_attack_move_puts_the_unit_at_its_tile_with_the_aggressive_stance_until_calm():
    r, sent = jump([ev(1000, "stance", stance="Defensive"), ev(2000, "attack_move", tile=[10.5, 10.5])])
    assert "tp u2 42.5 70.0 42.5" in sent
    assert sent.index("aoe stance u2 aggressive") > sent.index("aoe stance u2 defensive")
    assert r.charging == {8: "defensive"} and r.calm([8]) == ["aoe stance u2 defensive"]


def test_a_later_move_ends_the_patrol_and_a_stop_ends_the_walk():
    r, sent = jump([ev(1000, "patrol", tile=[10.5, 10.5]), ev(2000, "move", tile=[3.5, 3.5])])
    assert 8 not in r.patrols and "tp u2 14.5 70.0 14.5" in sent
    r, sent = jump([ev(1000, "move", tile=[10.5, 10.5]), ev(1500, "stop")])
    assert "aoe stop u2" in sent and not r.moving
    assert not any(c.startswith("tp u2 42.5") for c in sent)       # it stopped near its place, not at the tile


def test_a_follow_and_a_formation_of_the_skipped_time_are_kept():
    r, _ = jump([ev(1000, "formation", formation="Box"), ev(2000, "follow", target=7)])
    assert r.formations[8] == "Box" and r.follows[8][:2] == [7, "follow"]
