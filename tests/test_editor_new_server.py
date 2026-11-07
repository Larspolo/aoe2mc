"""A new map of the editor of each AoE2 DE size (#6079, epic #6073): new_world gives a world of the tiles of the size
name, and on a real server a new map with one unit saves and converts back to the same map."""
import contextlib
import io
import json
import os
import sys

import pytest
from test_mc_check import mojang_reachable

import aoe2mc
import rmap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
TERRAIN, PLAYERS = "DESERT_SAND", 3
BIG = max(rmap.MAP_SIZES.values())


def new(path, size):
    """The aoe2mc.json of a new world of the size name at path."""
    import editor
    with contextlib.redirect_stdout(io.StringIO()):
        editor.new_world(path, aoe2mc.map_size(size), TERRAIN, PLAYERS)
    with open(os.path.join(path, "aoe2mc.json")) as f:
        return json.load(f)


def active(data):
    return sorted(int(p) for p, v in data["players"].items() if int(p) and v.get("active"))


@pytest.mark.parametrize("size", [pytest.param(k, marks=pytest.mark.slow) if v == BIG else k
                                  for k, v in sorted(rmap.MAP_SIZES.items())])
def test_each_size_name_gives_its_tiles(tmp_path, size):
    data = new(str(tmp_path / "W"), size)
    assert data["map_size"] == rmap.MAP_SIZES[size]
    assert len(data["terrain"]) == rmap.MAP_SIZES[size]
    assert active(data) == list(range(1, PLAYERS + 1))


@pytest.mark.mc
def test_new_map_saves_and_converts_back(tmp_path):
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    import editor
    import export

    from game import run
    size = min(rmap.MAP_SIZES, key=rmap.MAP_SIZES.get)
    world, out = str(tmp_path / "W"), str(tmp_path / "OUT.aoe2scenario")
    data = new(world, size)
    T = data["tile_size"]
    name = dict(editor.tabs())["units"][0]
    tile = (data["map_size"] // 2 + 3, data["map_size"] // 2 + 3)
    with run.Game(world) as game:
        game.forceload()
        s = editor.State(game, data)
        s.player = 1
        o = editor.place_at(s, "p", name, (tile[0] * T + T // 2, tile[1] * T + T // 2))
        assert o is not None and o["player"] == 1
        with contextlib.redirect_stdout(io.StringIO()):
            editor.save(game, out, s)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W2"))
    with open(os.path.join(tmp_path, "W2", "aoe2mc.json")) as f:
        back = json.load(f)
    assert back["map_size"] == data["map_size"]
    assert back["terrain"] == data["terrain"]
    assert active(back) == active(data)
    got = [(o.get("id"), o.get("player"), *map(int, o["tile"])) for o in back["objects"]]
    assert (export.unit_id(name), 1, *tile) in got, got
