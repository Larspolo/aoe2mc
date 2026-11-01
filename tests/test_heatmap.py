"""The walk heat map of a record (#5455)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import heatmap  # noqa: E402

RED, BLUE = (200, 0, 0), (0, 0, 200)


def events():
    return ([{"kind": "move", "time": 1000 * i, "player": 1, "tile": [2, 3]} for i in range(3)]
            + [{"kind": "order", "time": 5000, "objects": [7], "tile": [5, 1]},
               {"kind": "research", "time": 100, "player": 1, "tile": [0, 0]}])


def test_counts():
    g = heatmap.grid(events(), {7: 2}, 8)
    assert g[1][2, 3] == 3 and g[2][5, 1] == 1
    assert g[1].sum() == 3 and g[2].sum() == 1


def test_time_range():
    g = heatmap.grid(events(), {7: 2}, 8, start=1000, end=5000)
    assert g[1][2, 3] == 2 and 2 not in g


def test_image():
    img = heatmap.image(heatmap.grid(events(), {7: 2}, 8), {1: RED, 2: BLUE})
    px = np.array(img)
    assert img.size == (8, 8)
    assert px[3, 2].tolist() == list(RED) and px[1, 5][2] > 0 and px[1, 5][:2].tolist() == [0, 0]
    px[3, 2] = px[1, 5] = 0
    assert not px.any()


def test_deterministic():
    a = heatmap.image(heatmap.grid(events(), {7: 2}, 8), {1: RED, 2: BLUE}).tobytes()
    assert a == heatmap.image(heatmap.grid(events(), {7: 2}, 8), {1: RED, 2: BLUE}).tobytes()
