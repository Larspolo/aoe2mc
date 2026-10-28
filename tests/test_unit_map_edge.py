"""A unit on the last column or row of a map that is not a multiple of 16 blocks: the search for a free block next to
a relic does not leave the map (#3026, entity_chunk). Each map is 30 tiles, 120 blocks at --tile-size 4."""
import contextlib
import io
import json

import aoe2mc


def write(path, x, y, extra):
    """A flat grass map with a militia on (x, y) and the relics of extra on the blocks next to it."""
    objects = [{"name": "MILITIA", "player": 1, "x": x, "y": y}]
    objects += [{"name": "RELIC", "x": ex, "y": ey} for ex, ey in extra]
    d = {"size": 30, "terrain": [[0] * 30 for _ in range(30)], "elevation": [[0] * 30 for _ in range(30)],
         "objects": objects, "players": {"1": {"civ": "BRITONS"}}}
    path.write_text(json.dumps(d))
    return str(path)


def convert(src, out):
    text = io.StringIO()
    with contextlib.redirect_stdout(text):
        aoe2mc.main([src, str(out)])
    return text.getvalue()


def test_a_unit_on_the_east_edge_stands_inside_the_map(tmp_path):
    src = write(tmp_path / "east.json", 29.9, 10.5, [(29.9, 10.5)])
    text = convert(src, tmp_path / "east")
    assert "units in a block (moved up): 0" in text
    assert (tmp_path / "east" / "level.dat").exists()


def test_a_unit_on_the_south_edge_stands_inside_the_map(tmp_path):
    src = write(tmp_path / "south.json", 10.5, 29.9, [(10.5, 29.9), (10.25, 29.9), (10.75, 29.9)])
    text = convert(src, tmp_path / "south")
    assert "units in a block (moved up): 0" in text
    assert (tmp_path / "south" / "level.dat").exists()
