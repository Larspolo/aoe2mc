"""The fight heat map of a record as a PNG (#5454): the attack orders of each player at the tile of the target."""
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]

import heat_map  # noqa: E402
import heatmap  # noqa: E402

RED, BLUE = (200, 0, 0), (0, 0, 200)


def events():
    # player 1 orders its unit to attack object 7 (of player 2) on tile (5, 1); a move is no attack
    return [{"kind": "order", "time": 5000, "player": 1, "objects": [3], "target": 7, "tile": [5, 1]},
            {"kind": "move", "time": 6000, "player": 1, "objects": [3], "tile": [2, 3]}]


def test_fight_grid_and_png(tmp_path):
    g = heatmap.grid(events(), {7: 2, 3: 1}, 8, kind="fight")
    assert g[1][5, 1] == 1 and g[1].sum() == 1
    out = tmp_path / "fight.png"
    heatmap.image(g, {1: RED, 2: BLUE}).save(out)
    img = Image.open(out)
    assert img.format == "PNG" and img.size == (8, 8)
    px = np.array(img.convert("RGB"))
    assert px[1, 5][0] > 0 and px[1, 5][1:].tolist() == [0, 0]
    px[1, 5] = 0
    assert not px.any()


def test_cli_fight_kind(tmp_path):
    world = tmp_path / "world"
    world.mkdir()
    data = {"timeline": events(), "map_size": 8,
            "objects": [{"ref": 7, "player": 2, "name": "Archer"}, {"ref": 3, "player": 1, "name": "Archer"}],
            "players": {"1": {"color": "red"}, "2": {"color": "blue"}}}
    (world / "aoe2mc.json").write_text(json.dumps(data))
    out = tmp_path / "fight.png"
    heat_map.main([str(world), str(out), "--kind", "fight"])
    px = np.array(Image.open(out).convert("RGB"))
    # only the target tile is lit, in the red of player 1 (the dye color of the player, not pure red)
    assert px.any(2).sum() == 1 and px[1, 5][0] > px[1, 5][2]
