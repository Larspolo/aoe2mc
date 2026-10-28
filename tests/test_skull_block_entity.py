"""#3032: each skull block has its `minecraft:skull` block entity: the 26.3 client draws a skull only with it."""
import contextlib
import io
import json

import aoe2mc
import world_reader


def test_each_skull_block_has_a_skull_block_entity(tmp_path):
    src = tmp_path / "skulls.json"
    src.write_text(json.dumps({"size": 32, "terrain": [[0] * 32] * 32,
                               "objects": [{"name": "HEAD", "x": 8.5, "y": 8.5},
                                           {"name": "IMPALED_CORPSE", "x": 12.5, "y": 8.5},
                                           {"name": "PAGAN_SHRINE", "player": 1, "x": 20, "y": 20}],
                               "players": {"1": {"civ": "LITHUANIANS", "color": 0}}}))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(str(src), str(tmp_path / "W"))
    w = world_reader.World(str(tmp_path / "W"))
    skulls = {(int(be["x"]), int(be["y"]), int(be["z"])) for c in w.chunks().values() for be in c["block_entities"]
              if str(be["id"]) == "minecraft:skull"}
    blocks = {p for p in skulls if "skull" in w.block(*p)}
    assert len(skulls) >= 5 and blocks == skulls
    assert aoe2mc.block_entity_type("minecraft:piston_head[facing=up]") is None
