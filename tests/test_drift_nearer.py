"""The drift table counts no stray for a move nearer to the replay position at the end of a walk (#1333): "nearer"
compares the raw distances, not the distances less the slack of the leg."""
import replay_drift


def row(t, x, z, slack):
    return {"uuid": "u", "name": "EAGLE_SCOUT", "t": t, "x": x, "y": 76.0, "z": z, "rx": 296.5, "rz": 126.5,
            "slack": slack, "order": False, "target": False}


def test_a_move_nearer_at_the_end_of_a_walk_is_no_stray():
    rows = [row(194_700, 296.31, 128.59, 3.86), row(204_800, 295.57, 125.91, 0.0)]   # the log rows of #1333
    assert replay_drift.analyze(rows)["EAGLE_SCOUT"]["stray"] == 0


def test_a_move_away_is_a_stray():
    rows = [row(194_700, 296.31, 128.59, 3.86), row(204_800, 296.0, 131.5, 0.0)]     # 2.9 blocks away from it
    assert replay_drift.analyze(rows)["EAGLE_SCOUT"]["stray"] == 1
