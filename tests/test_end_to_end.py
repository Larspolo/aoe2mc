"""Convert the synthetic tiny scenario and read the world back."""
import json
import os

import aoe2mc
import mcvalid
import world_reader
from conftest import entity_ids


def test_world_files(tiny_world):
    path, _ = tiny_world
    dim = "dimensions/minecraft/overworld/"                       # 26.x layout
    for f in ("level.dat", "preview.png", dim + "region/r.0.0.mca", dim + "entities/r.0.0.mca"):
        assert os.path.exists(os.path.join(path, f)), f


def test_world_icon(tiny_world):
    from PIL import Image
    with Image.open(os.path.join(tiny_world[0], "icon.png")) as im:
        assert im.size == (64, 64)                                # the size of the Minecraft world list icon


def test_level_dat(tiny_world):
    level = world_reader.World(tiny_world[0]).level()
    assert int(level["DataVersion"]) == aoe2mc.DATA_VERSION
    assert str(level["LevelName"]) == "tiny"
    assert int(level["GameType"]) == 1
    assert float(level["spawn"]["yaw"]) == aoe2mc.SPAWN_YAW == -135  # look north-east, like the AoE2 camera (#23)


def test_chunks_have_valid_blocks_and_biomes(tiny_world):
    w = world_reader.World(tiny_world[0])
    chunks = w.chunks()
    assert len(chunks) == 64          # 24 tiles * 4 blocks = 96 blocks = 6 x 6 chunks, and a ring for the border
    for (cx, cz), c in chunks.items():
        assert int(c["DataVersion"]) == aoe2mc.DATA_VERSION
        assert (int(c["xPos"]), int(c["zPos"])) == (cx, cz)
        for s in c["sections"]:
            for b in s["biomes"]["palette"]:
                assert mcvalid.biome_error(str(b), aoe2mc.VERSION_NAME) is None
    assert mcvalid.invalid_states(w.palette(), aoe2mc.VERSION_NAME) == {}


def test_terrain_and_water(tiny_world):
    w = world_reader.World(tiny_world[0])
    assert w.block(90, aoe2mc.WATER_Y, 48) == "minecraft:water[level=0]"       # deep water at x >= 20 tiles
    assert w.block(90, aoe2mc.WATER_Y - 3, 48) == "minecraft:water[level=0]"


def test_diorama_border(tiny_world):
    """The default border (#172): the map stands on a plinth; the floor is 6 blocks under the lowest ground."""
    w = world_reader.World(tiny_world[0])
    column = [w.block(-1, y, 48) for y in range(aoe2mc.MIN_Y, aoe2mc.MAX_Y)]
    floor = aoe2mc.MIN_Y + next(i for i, b in enumerate(column) if b != "minecraft:air")
    assert column[floor - aoe2mc.MIN_Y] == "minecraft:polished_deepslate"
    assert "minecraft:stone_bricks" in column and "minecraft:polished_andesite" in column
    assert w.block(0, floor - 1, 48) == "minecraft:air" and w.block(0, floor, 48) != "minecraft:air"
    assert w.block(0, aoe2mc.MIN_Y, 0) == "minecraft:air"


def test_entities(tiny_world):
    path, out = tiny_world
    ents = world_reader.World(path).entities(flat=False)
    ids = [i for e in ents for i in entity_ids(e)]
    for i in ids:
        assert mcvalid.entity_error(i, aoe2mc.VERSION_NAME) is None, i
    assert "minecraft:horse" in ids and "minecraft:villager" in ids and "minecraft:skeleton" in ids
    assert "units in a block (moved up): 0" in out



def test_objects_file(tiny_world):
    """aoe2mc.json lists the map, the players and the objects; the unit UUIDs are the UUIDs of the entities."""
    path, _ = tiny_world
    with open(os.path.join(path, "aoe2mc.json")) as f:
        data = json.load(f)
    assert (data["tile_size"], data["level_height"]) == (4, 3) and data["map_size"] > 0
    assert all({"civ", "color", "arch"} <= set(p) for p in data["players"].values())
    objs = data["objects"]
    assert all({"id", "name", "kind", "player", "tile", "rotation"} <= set(o) for o in objs)
    world = {aoe2mc.units.uuid_str(e["UUID"]) for e in world_reader.World(path).entities()}
    uuids = [o["uuid"] for o in objs if o["kind"] == "unit"]
    assert uuids and set(uuids) <= world and len(set(uuids)) == len(uuids)
    blds = [o for o in objs if o["kind"] == "building"]
    assert blds and all(len(o["footprint"]) == 4 for o in blds)
    tc, = [o for o in blds if o["name"] == "TOWN_CENTER"]
    x0, z0, x1, z1 = tc["footprint"]
    assert x1 - x0 == z1 - z0 == 16 and x0 <= tc["tile"][0] * 4 <= x1
    ground = [row.split() for row in data["ground"]]                # y where a unit stands, "-" for water (#138)
    assert len(ground) == len(ground[0]) == data["map_size"] * 4 and any("-" in row for row in ground)
    stand = [(int(float(e["Pos"][1])), ground[int(float(e["Pos"][2]))][int(float(e["Pos"][0]))])
             for e in world_reader.World(path).entities() if "Pos" in e]
    land = [(y, g) for y, g in stand if g != "-"]
    assert land and all(y == int(g) for y, g in land)

def test_mc_version_26_3(tmp_path, monkeypatch):
    import contextlib
    import io

    import scenarios
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"), {"instructions": "Defend the town center."})
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([src, str(tmp_path / "W"), "--mc-version", "26.3"])
    w = world_reader.World(str(tmp_path / "W"))
    level = w.level()
    assert (int(level["DataVersion"]), str(level["Version"]["Name"])) == (5023, "26.3")
    assert {int(c["DataVersion"]) for c in w.chunks().values()} == {5023}
    assert {int(c["DataVersion"]) for c in w.chunks("entities").values()} == {5023}
    assert mcvalid.invalid_states(w.palette(), "26.3") == {}
    assert aoe2mc.MC["name"] == aoe2mc.VERSION_NAME               # convert() restores the default version
    # 26.x world layout and level.dat (docs/minecraft-versions.md)
    assert os.path.isdir(tmp_path / "W" / "dimensions" / "minecraft" / "overworld" / "region")
    assert not os.path.exists(tmp_path / "W" / "region")
    assert "spawn" in level and "SpawnX" not in level and "GameRules" not in level
    assert float(level["spawn"]["yaw"]) == aoe2mc.SPAWN_YAW         # the AoE2 camera view, as in 1.21.1 (#23)
    for f in ("game_rules", "world_gen_settings", "weather", "world_clocks"):
        assert os.path.exists(tmp_path / "W" / "data" / "minecraft" / f"{f}.dat"), f
    ents = w.entities()
    assert ents and not any(k in e for e in ents for k in ("ArmorItems", "HandItems", "FallDistance"))
    assert all(mcvalid.entity_error(str(e["id"]), "26.3") is None for e in ents)
    book, = [be["Book"] for c in w.chunks().values() for be in c["block_entities"] if "Book" in be]
    page = book["components"]["minecraft:written_book_content"]["pages"][0]["raw"]
    assert str(page["extra"][1]["text"]) == "Defend the town center."    # text components are NBT (1.21.5)
    # block renames of the version profile
    monkeypatch.setattr(aoe2mc, "MC", aoe2mc.VERSIONS["26.3"])
    assert dict(aoe2mc.B.nbt(aoe2mc.B("chain[axis=y]"))) == {"id": "minecraft:iron_chain",
                                                           "properties": {"axis": "y"}}


def test_book_of_scenario_texts(tmp_path):
    import contextlib
    import io

    import scenarios
    long = " ".join(f"word{i}" for i in range(200))
    src = scenarios.tiny(str(tmp_path / "book.aoe2scenario"),
                         {"instructions": "Defend the <BLUE>town center</BLUE>.", "history": long})
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "BookWorld"))
    assert "units in a block (moved up): 0" in out.getvalue()
    w = world_reader.World(str(tmp_path / "BookWorld"))
    sx, _, sz, _ = w.spawn()
    lecterns = [be for c in w.chunks().values() for be in c["block_entities"] if str(be["id"]) == "minecraft:lectern"]
    assert len(lecterns) == 1
    be = lecterns[0]
    x, y, z = int(be["x"]), int(be["y"]), int(be["z"])
    assert w.block(x, y, z).startswith("minecraft:lectern[") and "has_book=true" in w.block(x, y, z)
    assert w.block(x, y - 1, z) != "minecraft:air" and max(abs(x - sx), abs(z - sz)) <= 6
    book = be["Book"]["components"]["minecraft:written_book_content"]
    assert str(book["title"]["raw"]) == "book"
    def text(raw):                                                # 26.3: NBT compound, 1.21.1: JSON string
        if not hasattr(raw, "keys"):
            return json.loads(str(raw))
        return {"extra": [{k: bool(v) if k == "bold" else str(v) for k, v in e.items()} for e in raw["extra"]]}
    pages = [text(p["raw"]) for p in book["pages"]]
    assert pages[0]["extra"] == [{"text": "Instructions\n\n", "bold": True}, {"text": "Defend the town center."}]
    assert pages[1]["extra"][0]["text"] == "History\n\n" and len(pages) > 3      # the long text has more pages
    assert all(len(p["extra"][-1]["text"]) <= 14 * 19 for p in pages)


def test_no_book_without_texts(tiny_world):
    w = world_reader.World(tiny_world[0])
    assert not any(str(be["id"]) == "minecraft:lectern" for c in w.chunks().values() for be in c["block_entities"])


def test_mc_version_1_21_1(tmp_path):
    import contextlib
    import io

    import scenarios
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([src, str(tmp_path / "W"), "--mc-version", "1.21.1"])
    assert os.path.isdir(tmp_path / "W" / "region") and not os.path.exists(tmp_path / "W" / "dimensions")
    w = world_reader.World(str(tmp_path / "W"))
    level = w.level()
    assert (int(level["DataVersion"]), str(level["Version"]["Name"])) == (3955, "1.21.1")
    assert float(level["SpawnAngle"]) == aoe2mc.SPAWN_YAW and "GameRules" in level
    assert {int(c["DataVersion"]) for c in w.chunks().values()} == {3955}
    assert mcvalid.invalid_states(w.palette(), "1.21.1") == {}
    ids = [i for e in w.entities(flat=False) for i in entity_ids(e)]
    assert ids and all(mcvalid.entity_error(i, "1.21.1") is None for i in ids)
