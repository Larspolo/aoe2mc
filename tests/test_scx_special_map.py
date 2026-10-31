"""A special_map_* base scenario of format 1.35 (#5209): the scenario player data comes before the objects (115 bytes
for each player, #5316). The file is a small own file of that form, with trigger data after the objects."""
import numpy as np

import scx
from tests.test_scenario_de_135 import build


def test_special_map_form_reads_players_and_objects(tmp_path):
    terrain = np.arange(30, dtype=np.int16).reshape(6, 5) % 24
    path = build(tmp_path / "special_map_x.scx", "1.35", terrain, np.zeros((6, 5), np.float32), {1: 1, 2: 3},
                 [(0, 1.5, 2.5, 709), (1, 3.5, 1.5, 109), (2, 4.5, 0.5, 83)])
    s = scx.read(path)
    assert [(o["player"], o["type"], o["x"], o["y"]) for o in s["objects"]] == [
        (0, 709, 1.5, 2.5), (1, 109, 3.5, 1.5), (2, 83, 4.5, 0.5)]
    assert s["players"][1]["color"] == 0 and s["players"][2]["color"] == 1
