"""The item name of a heat map (#5671): the last command ends with "end=LABEL" (the kind and the time range), and the
plugin names the item "Heat map: LABEL"."""
import heatmap
import numpy as np
import replay
from test_replay_heat_demand import Deaths, data, moves


def test_item_label_is_the_end_token():
    a = np.zeros((4, 4), int)
    a[1, 2] = 3
    assert heatmap.item_commands({1: a}, {1: 25}, 4, 4, label="fight")[-1].endswith(" end=fight")
    assert heatmap.item_commands({1: a}, {1: 25}, 4, 4)[-1].endswith(" end=walk")
    assert heatmap.item_commands({}, {}, 4, 4, label="death") == ["aoe heatmap 4 4 end=death"]


def test_replay_label_has_the_range():
    r = replay.Replay(Deaths([]), data(moves()), ai=True)
    assert r.heat_commands("death", 600000, 1200000)[-1].endswith(" end=death,10:00-20:00")
    assert r.heat_commands("fight", 600000, None)[-1].endswith(" end=fight,10:00-now")
    assert r.heat_commands("walk")[-1].endswith(" end=walk")


def test_the_end_names_the_three_kinds():
    r = replay.Replay(Deaths(["Deaths: p2 4 4 1"]), data(moves()), ai=True)     # the death counts at the end
    labels = [c.split()[-1][len("end="):] for c in r.end_heat_commands() if c.split()[-1].startswith("end=")]
    assert labels == list(heatmap.KINDS)
