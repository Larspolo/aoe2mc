"""--orientation turns the timeline of a recorded game: a wall tile is a tile index, its middle turns (#3029)."""
import pytest

import aoe2mc

SIZE = 16


@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_wall_tiles_of_the_replay_are_the_turned_tiles(k):
    events = [{"kind": "wall", "tile": [0, 0], "end": [3, 0]}]
    aoe2mc.turn_timeline(events, SIZE, k)
    e = events[0]
    replay = [(x + 0.5, y + 0.5) for x, y in aoe2mc.wall_tiles(*e["tile"], *e["end"])]
    expected = [aoe2mc.turn_tile(x + 0.5, y + 0.5, SIZE, k) for x, y in aoe2mc.wall_tiles(0, 0, 3, 0)]
    assert replay == expected
    assert all(0 <= x < SIZE and 0 <= y < SIZE for x, y in replay)


def test_a_wall_at_the_map_edge_stays_on_the_map():
    events = [{"kind": "wall", "tile": [0, 0], "end": [3, 0]}]
    aoe2mc.turn_timeline(events, SIZE, 1)                   # se: the edge tile 0 goes to tile 15
    assert events[0]["tile"] == [15, 0] and events[0]["end"] == [15, 3]


@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_points_of_the_other_events_turn_as_before(k):
    events = [{"kind": "build", "tile": [5.25, 2.5]}, {"kind": "move", "tile": [1.0, 7.0], "end": [2.0, 3.0]}]
    aoe2mc.turn_timeline(events, SIZE, k)
    for e, tiles in zip(events, ([[5.25, 2.5]], [[1.0, 7.0], [2.0, 3.0]])):
        for key, tile in zip(("tile", "end"), tiles):
            assert e[key] == [round(float(v), 3) for v in aoe2mc.turn_tile(*tile, SIZE, k)]
