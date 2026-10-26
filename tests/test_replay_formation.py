"""Live replay: a group of a MOVE stops in a formation around the target, one unit per free cell (#410). Fake RCON."""
import math

from test_replay_walk import HOUSE, play, tps

VILS = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"u{i}", "ref": 10 + i, "tile": [2.5, 8.5 + i]}
        for i in range(6)]


def move(tile, objects=VILS):
    ids = [o["ref"] for o in objects if o["kind"] == "unit"]
    r, sent, _ = play([dict(time=0, player=1, kind="move", objects=ids, tile=tile, names=["VILLAGER_MALE"] * len(ids))],
                      objects)
    return r, [tps(sent, f"u{i - 10}")[-1] for i in ids]


def test_a_group_stops_in_rows_across_the_walk_direction():
    r, ends = move([10.5, 10.5])                                     # the group walks east
    assert len(set(ends)) == 6 and all(r.map.free(*c) for c in ends)
    assert all(math.dist(c, (42, 42)) <= 8 for c in ends)              # at most 2 tiles from the target
    assert (42, 42) in ends
    rows = sorted({x for x, _ in ends})
    assert len(rows) == 2 and all(sum(x == row for x, _ in ends) == 3 for row in rows)   # 2 rows of 3, across x
    north = sorted(ends, key=lambda c: (c[0], c[1]))[:3]               # the units keep their order in a row
    assert [c[1] for c in north] == sorted(c[1] for c in north)


def test_a_group_next_to_a_building_takes_free_cells():
    r, ends = move([5.0, 9.0], VILS + [HOUSE])                        # the target is next to the house
    assert len(set(ends)) == 6 and all(r.map.free(*c) for c in ends)
    assert all(math.dist(c, (20, 36)) <= 8 for c in ends)


def test_one_unit_goes_to_the_target_cell():
    r, ends = move([12.5, 3.5], VILS[:1])
    assert ends == [(50, 14)]
