"""tools/replay_drift.py (#1169): the end of a walk or a jump to the replay position is no stray move."""
import replay_drift


def s(t, x, rx=0, **flags):
    return {"t": t * 1000, "uuid": "a", "name": "EAGLE_SCOUT", "x": x, "z": 0, "rx": rx, "rz": 0, **flags}


def test_a_move_to_the_replay_position_is_not_stray():
    assert replay_drift.analyze([s(0, 3.7), s(10, 1)])["EAGLE_SCOUT"]["stray"] == 0     # ends its walk
    assert replay_drift.analyze([s(0, 51), s(10, 0)])["EAGLE_SCOUT"]["stray"] == 0      # jumps to its position


def test_a_move_away_from_the_replay_position_is_stray_without_a_fight():
    assert replay_drift.analyze([s(0, 0.5), s(10, 4.6)])["EAGLE_SCOUT"]["stray"] == 1
    assert replay_drift.analyze([s(0, 0.5), s(10, 4.6, target=True)])["EAGLE_SCOUT"]["stray"] == 0
