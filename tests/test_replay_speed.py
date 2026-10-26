"""tools/replay_drift.py (#829): the walk speed of the replay units that walk behind their replay position."""
import re

import replay_drift


def s(t, x, rx, order=True, uuid="a", name="VILLAGER_MALE", need=3.2):
    return {"t": t * 1000, "uuid": uuid, "name": name, "x": x, "z": 0.0, "rx": rx, "rz": 0.0, "order": order,
            "need": need}


def test_walk_speed_of_units_far_behind_with_an_order():
    samples = [s(t, 2.0 * t, 100) for t in range(0, 40, 10)]                       # 2 blocks/s, far behind
    samples += [s(t, 3.0 * t, 3.0 * t + 5, uuid="b") for t in range(0, 40, 10)]   # near its position: no move
    samples += [s(0, 0, 100, uuid="c"), s(10, 30, 100, order=False, uuid="c")]     # no order at the end
    samples += [s(0, 0, 100, uuid="d", name="SCOUT_CAVALRY", need=4.8), s(10, 48, 100, uuid="d", name="SCOUT_CAVALRY",
                                                                           need=4.8)]
    k = replay_drift.walk(samples)
    assert k["VILLAGER"] == {"moves": 3, "walk": 2.0, "need": 3.2, "part": 0.62}
    assert k["SCOUT_CAVALRY"] == {"moves": 1, "walk": 4.8, "need": 4.8, "part": 1.0}
    lines = replay_drift.walk_table(k).splitlines()
    assert lines[0].split() == ["Unit", "Moves", "Walk", "Need", "Part"]
    assert lines[1].split() == ["VILLAGER", "3", "2.0", "3.2", "62%"]


def test_the_slack_of_a_leg_counts_as_no_distance():
    samples = [dict(s(t, 2.0 * t, 100), slack=100 - 2.0 * t - 10) for t in range(0, 30, 10)]   # 10 blocks behind
    assert replay_drift.walk(samples) == {}


def test_an_old_log_without_need():
    samples = [{k: v for k, v in s(t, 2.0 * t, 100).items() if k != "need"} for t in (0, 10)]
    k = replay_drift.walk(samples)
    assert k["VILLAGER"]["part"] is None and re.search(r"VILLAGER +1 +2.0 +None +-", replay_drift.walk_table(k))
