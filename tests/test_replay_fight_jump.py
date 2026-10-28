"""A click on a fight of the list jumps the live replay there and puts the viewer above its place (#2950)."""
import replay
import replay_input as ri

FIGHTS = [{"start": 125000, "tile": [10, 20], "players": [1, 2], "units": 14},
          {"start": 5000, "tile": [3, 4], "players": [1, 2], "units": 11}]


def test_fight_value_jumps_forward_before_the_fight():
    control = {"time": 30000, "fights": FIGHTS}
    assert ri.apply(ri.FIGHT, control) == "Fight at 02:05"
    assert control["jump"] == 125000 - ri.FIGHT_LEAD and control["place"] == [10, 20]


def test_fight_value_jumps_back_when_the_fight_is_earlier():
    control = {"time": 600000, "fights": FIGHTS}
    ri.apply(ri.FIGHT + 1, control)
    assert control["jump"] == 0 < control["time"]               # 10 s before 0:05: the start; Replay.run restarts


def test_fight_value_without_a_fight_changes_nothing():
    control = {"time": 0, "fights": FIGHTS}
    assert ri.apply(ri.FIGHT + 2, control) is None and "jump" not in control


def test_place_is_above_the_ground_of_the_tile():
    assert ri.place_commands([10, 20], 4, 70) == ["gamemode spectator @a", f"tp @a 42.0 {70 + ri.FIGHT_HEIGHT} 82.0 0 90"]


def test_replay_place_view_uses_the_ground_height():
    r = object.__new__(replay.Replay)
    r.T, r.n = 4, 16
    r.ground = [[None] * 16 for _ in range(16)]
    r.ground[8][4] = 66
    assert r.place_view([1, 2])[-1] == f"tp @a 6.0 {66 + ri.FIGHT_HEIGHT} 10.0 0 90"
