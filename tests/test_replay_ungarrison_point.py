"""Live replay: units that leave a building on UNGARRISON walk to its last GATHER POINT and work there (#3826)."""
from test_replay_garrison import TREE, order, play, ungarrison


def point(t, target=None, tile=(3.5, 12.5)):
    return dict(time=t, player=1, kind="gather_point", objects=[50], target=target, tile=list(tile),
                names=["TOWN_CENTER"])


def test_released_villagers_gather_the_resource_of_the_gather_point():
    r, _ = play([order(0, [7, 8], 50), point(15000, target=20), ungarrison(20000)], 40000, extra=[TREE])
    assert r.garrisons == {}
    assert all(r.units[i].task not in (None, "none") for i in (7, 8))
    assert all(n["idle"] == 0 for n in r.eco().values())


def test_without_a_gather_point_they_stay_next_to_the_building():
    r, _ = play([order(0, [7, 8], 50), ungarrison(20000)], 40000, extra=[TREE])
    assert r.garrisons == {} and r.eco()[1]["idle"] == 2
