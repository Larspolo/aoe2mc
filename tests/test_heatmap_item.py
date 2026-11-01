"""The heat map as a map item at the replay end (#5457): heatmap.item_commands."""
import heatmap
import numpy as np


def entries(cmds):
    return [tuple(int(v) for v in t.split(",")) for c in cmds for t in c.split()[4:] if t != "end"]


def test_each_painted_tile_once_with_shade_and_player_color():
    a, b = np.zeros((4, 4), int), np.zeros((4, 4), int)
    a[0, 0], a[1, 2], b[1, 2], b[3, 3] = 1, 4, 2, 20
    cmds = heatmap.item_commands({1: a, 2: b}, {1: 25, 2: 28}, 4, 4)
    assert cmds[-1].endswith(" end") and all(c.startswith("aoe heatmap 4 4 ") for c in cmds)
    got = {(x, y): (c, s) for x, y, c, s in entries(cmds)}
    assert len(got) == len(entries(cmds)) == 3
    assert got[(1, 2)][0] == 25 and got[(3, 3)] == (28, heatmap.SHADES - 1)
    assert got[(0, 0)][1] < got[(1, 2)][1] < got[(3, 3)][1]


def test_long_grids_split_below_the_limit():
    g = np.ones((40, 40), int)
    cmds = heatmap.item_commands({1: g}, {1: 25}, 4, 40, limit=300)
    assert len(cmds) > 1 and all(len(c) <= 300 for c in cmds)
    assert len(entries(cmds)) == 1600 and cmds[-1].endswith(" end")


def test_no_events_still_gives_the_item():
    assert heatmap.item_commands({}, {}, 4, 8) == ["aoe heatmap 4 8 end"]
