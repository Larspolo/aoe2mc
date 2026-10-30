"""Convert the synthetic tiny scenario and read the world back."""
import json
import os

import aoe2mc
import mcvalid
import world_reader
from entities import entity_ids


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
    assert x1 - x0 == z1 - z0 == aoe2mc.buildings.footprint("TOWN_CENTER") * 4 and x0 <= tc["tile"][0] * 4 <= x1
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
    assert float(level["spawn"]["yaw"]) == aoe2mc.SPAWN_YAW         # the AoE2 camera view (#23)
    for f in ("game_rules", "world_gen_settings", "weather", "world_clocks"):
        assert os.path.exists(tmp_path / "W" / "data" / "minecraft" / f"{f}.dat"), f
    ents = w.entities()
    assert ents and not any(k in e for e in ents for k in ("ArmorItems", "HandItems", "FallDistance"))
    assert all(mcvalid.entity_error(str(e["id"]), "26.3") is None for e in ents)
    book, = [be["Book"] for c in w.chunks().values() for be in c["block_entities"] if "Book" in be]
    page = book["components"]["minecraft:written_book_content"]["pages"][0]["raw"]
    assert str(page["extra"][1]["text"]) == "Defend the town center."    # text components are NBT (1.21.5)


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
    lecterns = [be for c in w.chunks().values() for be in c["block_entities"]
                if str(be["id"]) == "minecraft:lectern" and "Book" in be]      # the town center has an empty one
    assert len(lecterns) == 1
    be = lecterns[0]
    x, y, z = int(be["x"]), int(be["y"]), int(be["z"])
    assert w.block(x, y, z).startswith("minecraft:lectern[") and "has_book=true" in w.block(x, y, z)
    assert w.block(x, y - 1, z) != "minecraft:air" and max(abs(x - sx), abs(z - sz)) <= 6
    book = be["Book"]["components"]["minecraft:written_book_content"]
    assert str(book["title"]["raw"]) == "book"
    def text(raw):                                                # an NBT compound (26.3)
        return {"extra": [{k: bool(v) if k == "bold" else str(v) for k, v in e.items()} for e in raw["extra"]]}
    pages = [text(p["raw"]) for p in book["pages"]]
    assert pages[0]["extra"] == [{"text": "Instructions\n\n", "bold": True}, {"text": "Defend the town center."}]
    assert pages[1]["extra"][0]["text"] == "History\n\n" and len(pages) > 3      # the long text has more pages
    assert all(len(p["extra"][-1]["text"]) <= 14 * 19 for p in pages)


def test_no_book_without_texts(tiny_world):
    w = world_reader.World(tiny_world[0])
    assert not any(str(be["id"]) == "minecraft:lectern" and "Book" in be
                   for c in w.chunks().values() for be in c["block_entities"])


def test_book_has_the_objectives(tmp_path):
    """The triggers that the game lists as objectives go into the book, in their order; other triggers do not (#360)."""
    import scenarios
    scn = scenarios.new_scenario(16)
    tm = scn.trigger_manager
    tm.add_trigger("Second", description="Keep the <RED>castle</RED>.", display_as_objective=True, description_order=2)
    tm.add_trigger("Spawn wolves", description="internal")
    tm.add_trigger("Find the relic", display_as_objective=True, description_order=1)
    src = str(tmp_path / "goals.aoe2scenario")
    scenarios.save(scn, src)
    texts = aoe2mc.read_scenario(src)[4]
    assert texts["objectives"] == "- Find the relic\n- Keep the <RED>castle</RED>."
    assert aoe2mc.book_pages(texts) == [("Objectives", "- Find the relic\n- Keep the castle.")]


def test_work_sounds(tiny_world, tmp_path):
    """The datapack plays a work sound at a building with a player near it: the bell at the town center (#220)."""
    path, out = tiny_world
    pack = os.path.join(path, "datapacks", "aoe2mc")
    with open(os.path.join(pack, "pack.mcmeta")) as f:
        assert json.load(f)["pack"]["pack_format"] == 121
    with open(os.path.join(pack, "data", "aoe2mc", "predicate", "rare.json")) as f:
        assert json.load(f)["type"] == "minecraft:random_chance"            # 26.x key
    with open(os.path.join(pack, "data", "aoe2mc", "function", "pulse.mcfunction")) as f:
        lines = f.read().splitlines()
    with open(os.path.join(path, "aoe2mc.json")) as f:
        tc, = [o for o in json.load(f)["objects"] if o["name"] == "TOWN_CENTER"]
    x0, z0, x1, z1 = tc["footprint"]
    bell = [line.split() for line in lines if "block.bell.use" in line]
    assert len(bell) == 1 and (int(bell[0][2]), int(bell[0][4])) == ((x0 + x1) // 2, (z0 + z1) // 2)
    assert "if entity @a[distance=..16]" in lines[0] and lines[-1].startswith("schedule function aoe2mc:pulse")
    assert "work sounds at buildings: " in out
    # no building with a sound: no pack
    import numpy as np
    ground = np.full((32, 32), 70)
    smith = {"kind": "B", "name": "BLACKSMITH", "footprint": [4, 4, 12, 12]}
    assert aoe2mc.write_datapack(str(tmp_path / "A"), [smith], ground) == (1, 0)
    house = dict(smith, name="HOUSE")
    assert aoe2mc.write_datapack(str(tmp_path / "B"), [house], ground) == (0, 0)
    assert os.path.exists(tmp_path / "B" / "datapacks" / "aoe2mc" / "pack.mcmeta")     # the map pulse (#3034)


def test_ambience(tiny_world, tmp_path):
    """Particles and sounds by the vanilla biome near each player; --ambience full adds custom biomes (#219)."""
    path, out = tiny_world
    with open(os.path.join(path, "datapacks", "aoe2mc", "data", "aoe2mc", "function", "pulse.mcfunction")) as f:
        lines = f.read().splitlines()
    amb = [line for line in lines if line.startswith("execute as @a at @s if biome ~ ~ ~ minecraft:")]
    assert amb and "ambience (particles and sounds by biome): " in out
    assert not os.path.exists(os.path.join(path, "datapacks", "aoe2mc", "data", "aoe2mc", "worldgen"))
    biomes = {str(b) for c in world_reader.World(path).chunks().values() for s in c["sections"]
              for b in s["biomes"]["palette"]}
    assert {line.split()[10] for line in amb} <= biomes and all(b.startswith("minecraft:") for b in biomes)
    # full: the columns use one custom biome per group, and the pack has their files
    import contextlib
    import io

    import scenarios
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "F"), ambience="full")
    biomes = {str(b) for c in world_reader.World(str(tmp_path / "F")).chunks().values() for s in c["sections"]
              for b in s["biomes"]["palette"]}
    groups = {b.split(":")[1] for b in biomes if b.startswith("aoe2mc:")}
    assert groups and groups <= set(aoe2mc.AMBIENCE)
    assert all(b.startswith("aoe2mc:") or b[10:] not in aoe2mc.AMBIENCE_GROUP for b in biomes)
    folder = tmp_path / "F" / "datapacks" / "aoe2mc" / "data" / "aoe2mc" / "worldgen" / "biome"
    assert {f.name for f in folder.iterdir()} == {g + ".json" for g in groups}
    assert "attributes" in json.loads((folder / f"{sorted(groups)[0]}.json").read_text())   # 26.x format
    pulse = (tmp_path / "F" / "datapacks" / "aoe2mc" / "data" / "aoe2mc" / "function" / "pulse.mcfunction").read_text()
    assert {line.split()[10] for line in pulse.splitlines() if " if biome " in line} == {f"aoe2mc:{g}" for g in groups
                                                                                       if any(aoe2mc.AMBIENCE[g][1:3])}
    swamp = aoe2mc.biome_file("swamp")
    assert swamp["effects"]["water_color"] == "#617b64" and swamp["effects"]["grass_color_modifier"] == "swamp"
    # off: the world as before #188: no datapack, the animals are silent too (#222)
    with contextlib.redirect_stdout(io.StringIO()) as log:
        aoe2mc.convert(src, str(tmp_path / "O"), ambience="off")
    assert not os.path.exists(tmp_path / "O" / "datapacks") and "work sounds" not in log.getvalue()
    sheep = [e for e in world_reader.World(str(tmp_path / "O")).entities() if str(e["id"]) == "minecraft:sheep"]
    assert sheep and all(e.get("Silent") == 1 for e in sheep)
    loud = [e for e in world_reader.World(path).entities() if str(e["id"]) == "minecraft:sheep"]
    assert loud and not any(e.get("Silent") for e in loud)                  # basic: animal sounds (#227)


def test_player_teams(tiny_world):
    """Each player with units is a team in the player color; its units have the tag that the pulse joins (#358)."""
    path, _ = tiny_world
    func = os.path.join(path, "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(func, "load.mcfunction")) as f:
        load = f.read().splitlines()
    with open(os.path.join(func, "start.mcfunction")) as f:     # the colors: at the first load only (#3074)
        load[:0] = f.read().splitlines()
    with open(os.path.join(func, "pulse.mcfunction")) as f:
        pulse = f.read().splitlines()
    with open(os.path.join(path, "aoe2mc.json")) as f:
        data = json.load(f)
    owners = {o["player"] for o in data["objects"] if o["kind"] == "unit" and o["player"]}
    teams = owners | {int(n) for n in data["players"] if 0 < int(n) <= 8}   # a player with no units has a team too (#3088)
    assert owners and {int(line.split()[2][1:]) for line in load if line.startswith("team add")} == teams
    for n in teams:
        color = aoe2mc.units.TEAM_COLOR[data["players"][str(n)]["color"]]
        assert f"team modify p{n} color {color}" in load and f"team join p{n} @e[tag=aoe2mc.p{n},team=]" in pulse
    assert load[-1].startswith("schedule") and pulse[-1].startswith("schedule")
    tags = {str(t) for e in world_reader.World(path).entities() for t in e.get("Tags", [])}
    gaia = {0} & {o["player"] for o in data["objects"] if o["kind"] == "unit"}   # the tag aoe2mc.p0, no team (#2916)
    assert {t for t in tags if not t.startswith(("aoe2mc.t", "aoe2mc.r"))} - {aoe2mc.units.MOUNT} == {f"aoe2mc.p{n}" for n in owners | gaia}
    types = {t for t in tags if t.startswith("aoe2mc.t")}                 # the unit type tags (#681)
    assert types and types <= {f"aoe2mc.t{o['id']}" for o in data["objects"] if o["kind"] == "unit"}
