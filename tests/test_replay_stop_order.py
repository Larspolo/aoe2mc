"""Live replay: the STOP order of the record stops the selected units where they are (#2549). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL, orders  # noqa: E402
from test_replay_attack import ENEMY, attacks  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402

FAR = dict(time=0, player=1, kind="move", objects=[7], tile=[35.5, 10.5], names=["VILLAGER_MALE"])


def game(objects=(VIL, HOUSE), ai=True):
    d = data([], n=160)
    d["objects"] += list(objects)
    return replay.Replay(Fake(), d, ai=ai)


def test_a_stop_ends_the_walk_of_the_unit():
    for ai in (True, False):
        r = game(ai=ai)
        r.commands(FAR)
        assert 7 in r.moving
        out = r.commands(dict(time=2000, player=1, kind="stop", objects=[7]))
        assert 7 not in r.moving and r.units[7].path == []
        assert ("aoe stop u1" in out) == ai
        sent = r.steps(60000)
        assert not orders(sent) and not any(c.startswith("tp u1 ") for c in sent)


def test_a_stopped_unit_stands_on_its_way_not_at_the_goal():
    r = game()
    r.commands(FAR)
    start, goal = r.units[7].leg[0], r.units[7].pos
    r.commands(dict(time=1000, player=1, kind="stop", objects=[7]))
    x = r.units[7].pos[0]
    assert start[0] < x < goal[0]
    assert r.at(r.units[7], 5000) == r.units[7].pos


def test_a_stop_ends_the_attack_of_a_military_unit():
    r = game((VIL, MIL, HOUSE, ENEMY))
    assert attacks(r.commands(dict(time=0, player=1, kind="order", objects=[8], target=20))) == ["aoe attack u2 e1"]
    assert r.commands(dict(time=1000, player=1, kind="stop", objects=[8])) == ["aoe stop u2"]


def test_a_stop_for_an_unknown_object_changes_nothing():
    r = game()
    r.commands(FAR)
    moving = dict(r.moving)
    assert r.commands(dict(time=1000, player=1, kind="stop", objects=[999])) == []
    assert r.moving == moving


class Where(Fake):
    """Fake RCON whose entities stand at AT (data get entity ... Pos)."""
    AT = (50.3, 70.0, 41.7)

    def command(self, cmd):
        super().command(cmd)
        return "u1 has the following entity data: [{}d, {}d, {}d]".format(*self.AT) if cmd.endswith(" Pos") else ""


def test_a_stopped_unit_stands_where_its_entity_is():
    d = data([], n=160)
    d["objects"] += [VIL, HOUSE]
    r = replay.Replay(Where(), d, ai=True)
    r.commands(FAR)
    r.commands(dict(time=1000, player=1, kind="stop", objects=[7]))
    assert r.units[7].pos == (50.3, 70.0, 41.7) and r.units[7].cell == (50, 41)
    assert r.at(r.units[7], 5000) == r.units[7].pos
