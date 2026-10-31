"""A DE scenario of format 1.33 or 1.35 (#5072): AoE2ScenarioParser has no layout before 1.36, so scx.py reads it.
It differs from 1.36 (genie-scx, format.rs): no "collide and correct" byte (data version 1.36), the objects come
before the scenario player data in 1.33 (1.35: after it, #5209; 115 bytes for each player, #5316); 1.33 also has no trigger count (data version 1.35). The test builds the file byte by
byte: no free sample file exists."""
import struct
import zlib

import numpy as np
import pytest

import aoe2mc
import scx


def s16(text):
    b = text.encode() + b"\0" if text else b""
    return struct.pack("<H", len(b)) + b


def build(path, fmt, terrain, elevation, civs, objects):
    """A DE file of format fmt (the data version is the format). terrain, elevation: [x, y] arrays. civs: {player:
    civilization}. objects: (player, x, y, type) tuples."""
    v = float(fmt)
    i = lambda *a: struct.pack(f"<{len(a)}i", *a)
    d = i(100) + struct.pack("<f", v)
    d += b"".join((f"Player {p}".encode() if p in civs else b"").ljust(256, b"\0") for p in range(1, 17))
    d += i(*[-1] * 16) + b"".join(i(1, 1, civs[p], 0) if p in civs else i(0, 0, 0, 0) for p in range(1, 17))
    d += b"\1" + struct.pack("<hhf", 0, 0, 0) + i(0) * 16 + s16("base.scx") + i(*[-1] * 6)   # civ locks (DE)
    d += s16("A base scenario") + s16("") * 9 + struct.pack("<IIIH", 0, 0, 0, 1)
    d += s16("") * 48 + i(0, 0, 0) * 16 + bytes(16) + i(-99)
    d += i(200, 200, 200, 100, 100, 0, 0) * 16 + i(-99)                      # start resources and colors
    d += i(1, 0, 0, 0, 0, 0) + i(0, 4, 900, 9000) + i(3) * 256 + bytes(16 * 12 * 60) + i(-99) + i(0) * 16
    d += bytes(4) + i(2, *[0] * 15) + i(5, 6) + i(0) * 16 + i(1, *[0] * 15) + i(7)   # teams; disabled techs, units, buildings
    d += i(0, 0, 0) + i(-1) * 16 + i(-99) + i(-1, -1) + i(-1) + bytes(16)   # modes, start ages, view, map type, priorities
    d += i(0) if v >= 1.35 else b""                                        # the number of triggers
    d += b"\x60\x0a" + s16("") + b"\x60\x0a" + s16("Empty")                 # water definition, color mood
    w, h = terrain.shape
    d += struct.pack("<IIBII", 0xDEADF00D, 2, 1, w, h)                       # map version 2: 7 bytes for each tile
    tile = np.zeros((h, w, 7), np.uint8)
    tile[:, :, 0], tile[:, :, 1], tile[:, :, 5:] = terrain.T, elevation.T, 255
    d += tile.tobytes() + struct.pack("<I", 9) + struct.pack("<7f", 200, 200, 100, 200, 100, 0, 75) * 8
    objs = b""
    for p in range(9):
        o = [o for o in objects if o[0] == p]
        objs += struct.pack("<I", len(o))
        for k, (_, x, y, t) in enumerate(o):
            objs += struct.pack("<fffiHBfhi", x, y, 0, k, t, 2, 0, 0, -1)
    players = struct.pack("<I", 9)
    for p in range(1, 9):
        players += s16(f"Player {p}") + struct.pack("<ffhhB", -1, -1, 0, 0, 0) + struct.pack("<h", 9) + bytes(9)
        players += i(0) * 9 + i(p - 1) + struct.pack("<fiB", 2.0, 0, 0) + i(0, 0, 0, -1 if v >= 1.35 else 0)
    d += players + objs if v >= 1.35 else objs + players                   # 1.35: the players first, #5209
    d += struct.pack("<d", 2.2)                                              # triggers: not read
    header = struct.pack("<II", 6, 0) + struct.pack("<I", 0) + i(0, 2) + i(0, 0) + s16("") + i(0)
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    with open(path, "wb") as f:
        f.write(fmt.encode() + struct.pack("<I", len(header)) + header + c.compress(d) + c.flush())
    return path


TERRAIN = (np.arange(30, dtype=np.int16).reshape(6, 5) % 24)              # [x, y]: 6 wide, 5 high
ELEVATION = (np.arange(30).reshape(6, 5) % 3).astype(np.float32)


@pytest.mark.parametrize("fmt", ["1.33", "1.35"])
def test_scx_reads_the_map_and_objects(tmp_path, fmt):
    s = scx.read(build(tmp_path / "base.scx", fmt, TERRAIN, ELEVATION, {1: 1, 2: 2}, [(1, 2.5, 1.5, 83), (0, 4.5, 3.5, 59)]))
    assert (s["format"], s["width"], s["height"]) == (fmt, 6, 5)
    assert (s["terrain"] == TERRAIN).all() and (s["elevation"] == ELEVATION).all()
    assert [(o["player"], o["type"], o["x"], o["y"]) for o in s["objects"]] == [(0, 59, 4.5, 3.5), (1, 83, 2.5, 1.5)]
    assert s["players"][1] == {"civ": scx.CIVS[1], "color": 0, "view": None} and set(s["players"]) == {0, 1, 2}


@pytest.mark.parametrize("fmt", ["1.33", "1.35"])
def test_read_map_gives_the_map_of_the_file(tmp_path, fmt):
    path = build(tmp_path / "base.scx", fmt, TERRAIN, ELEVATION, {1: 1}, [(1, 2.5, 1.5, 83)])
    size, terrain, elevation, _, _, objects, players = aoe2mc.read_map(str(path))
    assert size == 6 and (terrain[:, :5] == TERRAIN).all() and (elevation[:, :5] == ELEVATION).all()
    assert [(o["player"], o["id"], o["x"], o["y"]) for o in objects] == [(1, 83, 2.5, 1.5)]
    assert players[1]["civ"] == scx.CIVS[1]


def test_a_de_scenario_file_of_format_135_reads_too(tmp_path):
    path = build(tmp_path / "base.aoe2scenario", "1.35", TERRAIN, ELEVATION, {1: 1}, [])
    assert aoe2mc.read_map(str(path))[0] == 6
