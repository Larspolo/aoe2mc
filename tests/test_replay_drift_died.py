"""tools/replay_drift.py: "died" counts a unit only when it is gone in all later samples (#3047)."""
import replay_drift


def s(t, x, z):
    return {"t": t * 1000, "uuid": "a", "name": "VILLAGER_MALE", "x": x, "z": z, "rx": 0, "rz": 0}


def test_a_unit_that_comes_back_did_not_die():
    k = replay_drift.analyze([s(0, 0, 0), s(10, None, None), s(20, 0, 0)])
    assert k["VILLAGER"]["died"] == 0


def test_a_unit_gone_in_all_later_samples_died():
    k = replay_drift.analyze([s(0, 0, 0), s(10, None, None), s(20, None, None)])
    assert k["VILLAGER"]["died"] == 1
