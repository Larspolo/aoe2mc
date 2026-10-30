"""aoe2mc.read_json: a map description in JSON converts with no scenario file (#960)."""
import contextlib
import io
import json

import pytest
import world_reader

import aoe2mc


def write(path, **kw):
    """A 16 × 16 grass map (terrain 0) with deep water (22) in the east, a raised corner, a town center and a villager
    of player 1, two oak trees and a gold mine. kw changes the keys of the description."""
    terrain = [[22 if x >= 12 else 0] * 16 for x in range(16)]
    elevation = [[1 if x < 3 and y < 3 else 0 for y in range(16)] for x in range(16)]
    d = {"size": 16, "terrain": terrain, "elevation": elevation,
         "objects": [{"name": "TOWN_CENTER", "player": 1, "x": 6.0, "y": 6.0},
                     {"name": "VILLAGER_MALE", "player": 1, "x": 9.5, "y": 4.5},
                     {"name": "TREE_OAK", "player": 0, "x": 2.5, "y": 12.5},
                     {"name": "TREE_OAK", "player": 0, "x": 3.5, "y": 13.5},
                     {"name": "GOLD_MINE", "player": 0, "x": 9.5, "y": 11.5}],
         "players": {"1": {"civ": "BRITONS"}}} | kw
    path.write_text(json.dumps(d))
    return str(path)


def test_read_json(tmp_path):
    size, terrain, elevation, names, texts, objects, players = aoe2mc.read_json(write(tmp_path / "m.json"))
    assert size == 16 and terrain[13, 0] == 22 and terrain[0, 0] == 0 and elevation[1, 1] == 1
    assert names[22] == "WATER_DEEP"
    tc = objects[0]
    assert (tc["kind"], tc["name"], tc["player"], tc["x"], tc["y"], tc["ref"]) == ("B", "TOWN_CENTER", 1, 6.0, 6.0, 0)
    assert [o["kind"] for o in objects] == ["B", "U", "O", "O", "O"]
    assert players[1] == {"color": "blue", "arch": "western", "civ": "BRITONS", "view": None}
    assert players[0]["civ"] == "GAIA"


def test_convert_a_json_map(tmp_path):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([write(tmp_path / "m.json"), str(tmp_path / "W"), "--preview"])
    text = out.getvalue()
    assert "player 1: britons, blue, western buildings" in text and "units in a block (moved up): 0" in text
    assert (tmp_path / "W" / "preview.png").exists()
    w = world_reader.World(str(tmp_path / "W"))
    states = {n.split("[")[0] for c in w.chunks().values() for s in c["sections"] for n in w.section_states(s)[0]}
    assert {"minecraft:grass_block", "minecraft:water", "minecraft:bell", "minecraft:gold_ore"} <= states
    assert any("oak_log" in n for n in states)                               # the trees
    assert w.block(13 * 4, aoe2mc.WATER_Y, 8 * 4).startswith("minecraft:water")
    assert any(str(e["id"]) == "minecraft:villager" for e in w.entities())


@pytest.mark.parametrize("kw, error", [({"objects": [{"name": "NO_SUCH_THING", "x": 1, "y": 1}]}, "unknown name 'NO_SUCH_THING'"),
                                       ({"terrain": [[999] * 16] * 16}, r"unknown terrain IDs \[999\]"),
                                       ({"terrain": [[0] * 4] * 4}, '"terrain" must be 16 lists of 16 numbers'),
                                       ({"size": 0}, '"size" must be a positive integer')])
def test_a_bad_json_map_gives_a_clear_error(tmp_path, kw, error):
    with pytest.raises(aoe2mc.OptionError, match=error):
        aoe2mc.read_json(write(tmp_path / "m.json", **kw))
