"""scx.py: read an old scenario (format 1.21) that the test builds byte by byte (#311). No free sample file exists."""
import struct
import zlib

import numpy as np
import pytest

import scx


def s16(text):
    b = text.encode() + b"\0" if text else b""
    return struct.pack("<H", len(b)) + b


def build(path, terrain, elevation, players, objects=(), fmt=b"1.21"):
    """A format 1.21 file (data version 1.22, AoC) with empty texts. terrain, elevation: [x, y] arrays.
    players: {id: (civilization, color, view)}. objects: (player, x, y, type) tuples."""
    i = lambda *v: struct.pack(f"<{len(v)}i", *v)
    d = i(100) + struct.pack("<f", 1.22)                                     # next object ID, data version
    d += b"".join((f"Player {p}".encode() if p in players else b"").ljust(256, b"\0") for p in range(1, 17))
    d += i(*[-1] * 16)                                                       # string table IDs of the names
    d += b"".join(i(1, 1, players[p][0], 0) if p in players else i(0, 0, 0, 0) for p in range(1, 17))
    d += b"\1" + struct.pack("<hhf", 0, 0, 0) + s16("test.scx") + i(*[-1] * 6)
    d += s16("A test scenario") + s16("") * 9                                # texts, cinematics, bitmap name
    d += struct.pack("<IIIH", 0, 0, 0, 1)                                    # no bitmap
    d += s16("") * 48 + i(0, 0, 0) * 16 + bytes(16) + i(-99)                 # AI files
    d += i(200, 200, 200, 100, 100, 0) * 16 + i(-99)                         # start resources
    d += i(1, 0, 0, 0, 0, 0) + i(0, 4, 900, 9000) + i(3) * 256 + bytes(16 * 12 * 60) + i(-99) + i(0) * 16
    d += i(0) * 16 + i(-1) * 480 + i(0) * 16 + i(-1) * 480 + i(0) * 16 + i(-1) * 320   # disabled techs, units, buildings
    d += i(0, 0, 0) + i(-1) * 16 + i(-99) + i(-1, -1) + i(-1)               # modes, start ages, view, map type
    w, h = terrain.shape
    d += struct.pack("<II", w, h)
    d += np.stack([terrain.T, elevation.T.astype(np.int8).view(np.uint8), np.zeros((h, w))], -1).astype(np.uint8).tobytes()
    d += struct.pack("<I", 9) + struct.pack("<7f", 200, 200, 100, 200, 100, 0, 75) * 8
    for p in range(9):
        objs = [o for o in objects if o[0] == p]
        d += struct.pack("<I", len(objs))
        for k, (_, x, y, t) in enumerate(objs):
            d += struct.pack("<fffiHBfhi", x, y, 0, k, t, 2, 0, 0, -1)
    d += struct.pack("<I", 9)
    for p in range(1, 9):
        civ, color, view = players.get(p, (0, p - 1, (-1, -1)))
        d += s16(f"Player {p}") + struct.pack("<ffhhB", *view, 0, 0, 0) + struct.pack("<h", 9) + bytes(9)
        d += i(0) * 9 + i(color) + struct.pack("<fiB", 2.0, 0, 0) + i(0, 0, 0, 0)
    d += struct.pack("<d", 1.6)                                              # triggers: not read
    header = struct.pack("<II", 2, 0) + struct.pack("<I", 0) + i(0, 2)       # version 2: time stamp, no text
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    with open(path, "wb") as f:
        f.write(fmt + struct.pack("<I", len(header)) + header + c.compress(d) + c.flush())
    return path


def test_read_map_and_players(tmp_path):
    terrain = np.arange(12, dtype=np.int16).reshape(4, 3)                    # [x, y]: 4 wide, 3 high
    elevation = np.array([[0, 1, 2], [0, 0, 1], [3, 0, 0], [0, 0, 7]], np.float32)
    path = build(tmp_path / "old.scx", terrain, elevation,
                 {1: (15, 1, (2.5, 1.5)), 2: (1, 0, (-1, -1))}, objects=[(1, 2.5, 1.5, 83)])
    s = scx.read(path)
    assert (s["format"], s["width"], s["height"]) == ("1.21", 4, 3)
    assert (s["terrain"] == terrain).all() and (s["elevation"] == elevation).all()
    assert s["players"][1] == {"civ": scx.CIVS[15], "color": 1, "view": (2.5, 1.5)}
    assert s["players"][2] == {"civ": scx.CIVS[1], "color": 0, "view": None}
    assert set(s["players"]) == {0, 1, 2}


def test_unknown_format_names_the_version(tmp_path):
    path = build(tmp_path / "new.scx", np.zeros((2, 2), np.int16), np.zeros((2, 2)), {}, fmt=b"1.11")
    with pytest.raises(scx.ScxError, match="'1.11' is not supported"):
        scx.read(path)


def test_convert_an_old_scenario(tmp_path):
    """aoe2mc.py IN.scx OUT (#312): a 16 x 16 grass map with water, a town center, a villager and a tree."""
    import contextlib
    import io

    import aoe2mc
    import buildings
    import world_reader
    terrain = np.zeros((16, 16), np.int16)
    terrain[12:, :] = 22                                                     # deep water in the east
    elevation = np.zeros((16, 16), np.float32)
    elevation[:3, :3] = 1
    path = build(tmp_path / "old.scx", terrain, elevation, {1: (1, 1, (6.0, 6.0))},
                 objects=[(1, 6.0, 6.0, 109), (1, 9.5, 4.5, 83), (0, 2.5, 12.5, 399)])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([str(path), str(tmp_path / "W")])
    text = out.getvalue()
    arch = buildings.CIV_TO_ARCH.get(scx.CIVS[1], "western")
    assert f"player 1: {scx.CIVS[1].lower()}, red, {arch} buildings" in text and "units in a block (moved up): 0" in text
    w = world_reader.World(str(tmp_path / "W"))
    states = {n for c in w.chunks().values() for s in c["sections"] for n in w.section_states(s)[0]}
    assert {"minecraft:grass_block", "minecraft:water", "minecraft:bell"} <= {n.split("[")[0] for n in states}
    assert any("log" in n for n in states)                                   # the tree
    assert any(str(e["id"]) == "minecraft:villager" for e in w.entities())
    assert w.block(13 * 4, aoe2mc.WATER_Y, 8 * 4).startswith("minecraft:water")


def test_convert_an_unknown_format_gives_a_clear_error(tmp_path, capsys):
    import aoe2mc
    path = build(tmp_path / "new.scx", np.zeros((2, 2), np.int16), np.zeros((2, 2)), {}, fmt=b"1.11")
    with pytest.raises(SystemExit):
        aoe2mc.main([str(path), str(tmp_path / "W")])
    assert "'1.11' is not supported" in capsys.readouterr().err
