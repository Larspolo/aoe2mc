"""Live replay: the FORMATION action of the record sets the shape of the next walks of the group (#2553): Line (#410),
Staggered, Flank and Box. Fake RCON (vanilla walks: one tp per cell)."""
import math

from test_replay_walk import play, tps


def units(names):
    return [{"kind": "unit", "name": name, "player": 1, "uuid": f"u{i}", "ref": 10 + i, "tile": [2.5, 4.5 + i]}
            for i, name in enumerate(names)]


def walk(names, formation=None, x=10.5):
    objects = units(names)
    tile = (x, sum(o["tile"][1] for o in objects) / len(objects))  # straight east of the group
    ids = [o["ref"] for o in objects]
    timeline = [dict(time=0, player=1, kind="formation", objects=ids, formation=formation)] * (formation is not None)
    timeline += [dict(time=1000, player=1, kind="move", objects=ids, tile=list(tile), names=list(names))]
    _, sent, _ = play(timeline, objects)
    return [tps(sent, f"u{i}")[-1] for i in range(len(names))]


def front(ends):
    """The z of the units in the first row of a walk to the east (the largest x)."""
    x = max(c[0] for c in ends)
    return sorted(z for cx, z in ends if cx == x)


def test_without_a_formation_the_group_walks_in_a_line():
    assert walk(["MILITIA"] * 6) == walk(["MILITIA"] * 6, "Line")
    z = front(walk(["MILITIA"] * 6))
    assert len(z) == 3 and {b - a for a, b in zip(z, z[1:])} == {2}  # FORMATION blocks apart


def test_staggered_doubles_the_gaps():
    z = front(walk(["MILITIA"] * 6, "Staggered"))
    assert len(z) == 3 and {b - a for a, b in zip(z, z[1:])} == {4}


def test_flank_splits_a_row_into_two_halves():
    ends = walk(["MILITIA"] * 8, "Flank")
    assert len(set(ends)) == 8
    z = front(ends)
    gaps = sorted(b - a for a, b in zip(z, z[1:]))
    assert gaps[-1] >= 5 * 2 and gaps[0] == 2                         # 4 empty slots between the halves


def test_box_puts_the_archer_inside():
    ends = walk(["MILITIA"] * 4 + ["ARCHER"] + ["MILITIA"] * 4, "Box")
    assert len(set(ends)) == 9
    cx, cz = (sum(c[k] for c in ends) / 9 for k in (0, 1))
    archer = ends[4]
    assert all(math.dist(archer, (cx, cz)) < math.dist(c, (cx, cz)) for i, c in enumerate(ends) if i != 4)


def test_the_formation_of_the_record_is_kept_for_later_walks():
    objects = units(["MILITIA"] * 6)
    ids = [o["ref"] for o in objects]
    timeline = [dict(time=0, player=1, kind="formation", objects=ids, formation="Staggered"),
                dict(time=1000, player=1, kind="move", objects=ids, tile=[6.5, 7.0], names=["MILITIA"] * 6),
                dict(time=60000, player=1, kind="move", objects=ids, tile=[12.5, 7.0], names=["MILITIA"] * 6)]
    _, sent, _ = play(timeline, objects)
    z = front([tps(sent, f"u{i}")[-1] for i in range(6)])
    assert len(z) == 3 and {b - a for a, b in zip(z, z[1:])} == {4}
