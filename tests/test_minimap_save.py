"""#2677 (epic #2580): a saved game keeps the explored tiles of the minimap of each player (fog.minimap), and the
first update after the load sends them again as `aoe minimap dim` runs."""
import json

from test_loom import setup

from game import fog, savegame

EXPLORED = {(1, 1), (2, 1), (3, 1), (7, 1), (2, 5)}


def loaded():
    _, g = setup()
    g.fog = {"hidden": set(), "at": None, "explored": set(EXPLORED), "map": (set(), set(EXPLORED))}
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    _, h = setup()
    savegame.load(h, d)
    return d, h


def test_the_explored_tiles_go_through_the_save_as_row_runs():
    d, h = loaded()
    assert d["players"]["1"]["explored"] == [[1, 1, 3], [1, 7, 7], [5, 2, 2]]
    assert h.fog["explored"] == EXPLORED


def test_the_first_minimap_after_the_load_dims_each_explored_tile():
    _, h = loaded()
    h.data["map_size"] = 16
    out = fog.minimap(h, h.fog)
    assert out[0] == f"aoe minimap fog {h.map.T} 16 p1"
    dim = {(tx, int(y)) for c in out if c.startswith("aoe minimap dim p1 ")
           for y, x0, x1 in (r.split(",") for r in c.split()[4:]) for tx in range(int(x0), int(x1) + 1)}
    assert dim == EXPLORED


def test_a_game_with_no_explored_tile_saves_no_key():
    _, g = setup()
    assert "explored" not in savegame.dump(g)["players"]["1"]
