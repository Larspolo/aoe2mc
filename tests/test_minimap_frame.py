"""A glow item frame at the spawn holds the map of the whole world (#839): next to the lectern of the scenario
texts, or in its place."""
import contextlib
import io
import math

import world_reader

import aoe2mc


def frames(path):
    return [e for e in world_reader.World(path).entities() if str(e["id"]) == "minecraft:glow_item_frame"]


def test_the_tiny_world_has_the_map_in_a_frame_at_the_spawn(tiny_world):
    path, out = tiny_world
    ents = frames(path)
    assert len(ents) == 1
    e = ents[0]
    assert str(e["Item"]["id"]) == "minecraft:filled_map" and int(e["Item"]["components"]["minecraft:map_id"]) == 0
    assert int(e["Facing"]) == 1 and int(e["Fixed"]) == 1 and int(e["Invulnerable"]) == 1
    x, y, z = (int(v) for v in e["block_pos"])
    assert [float(v) for v in e["Pos"]] == [x + 0.5, y + 1 / 32, z + 0.5]
    sx, sy, sz, _ = world_reader.World(path).spawn()
    assert math.dist((x, z), (sx, sz)) <= 4
    w = world_reader.World(path)
    assert w.block(x, y, z) == "minecraft:air" and w.block(x, y - 1, z) != "minecraft:air"   # on the ground
    assert "units in a block (moved up): 0" in out


def test_the_frame_stands_next_to_the_lectern(tmp_path):
    import scenarios
    src = scenarios.tiny(str(tmp_path / "book.aoe2scenario"), {"instructions": "Defend the town center."})
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "BookWorld"))
    w = world_reader.World(str(tmp_path / "BookWorld"))
    be = next(be for c in w.chunks().values() for be in c["block_entities"]
              if str(be["id"]) == "minecraft:lectern" and "Book" in be)
    (e,) = frames(str(tmp_path / "BookWorld"))
    x, y, z = (int(v) for v in e["block_pos"])
    assert abs(x - int(be["x"])) + abs(z - int(be["z"])) == 1
