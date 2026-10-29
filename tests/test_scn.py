"""scx.py: read the .scn scenarios of The Age of Kings (formats 1.18, 1.19, 1.20, #3860), built byte by byte."""
import struct
import zlib

import numpy as np
import pytest

import scx

DATA = {b"1.18": 1.15, b"1.19": 1.17, b"1.20": 1.18}     # format -> a data version of TribeScen in that format


def s16(text):
    b = text.encode() + b"\0" if text else b""
    return struct.pack("<H", len(b)) + b


def build(path, fmt, terrain, elevation, players, objects=()):
    """A file of format fmt with empty texts, the fields of its data version (the conditions of scx.tribe_scen).
    terrain, elevation: [x, y] arrays. players: {id: (civilization, color, view)}. objects: (player, x, y, type)."""
    v = DATA[fmt]
    i = lambda *a: struct.pack(f"<{len(a)}i", *a)
    d = i(100) + struct.pack("<f", v)
    d += b"".join((f"Player {p}".encode() if p in players else b"").ljust(256, b"\0") for p in range(1, 17))
    d += i(*[-1] * 16) if v > 1.16 else b""
    d += b"".join(i(1, 1, players[p][0], 0) if p in players else i(0, 0, 0, 0) for p in range(1, 17))
    d += b"\1" + struct.pack("<hhf", 0, 0, 0) + s16("test.scn") + i(*[-1] * 5)
    d += s16("A test scenario") + s16("") * 8                                # texts, cinematics, bitmap name
    d += struct.pack("<IIIH", 0, 0, 0, 1)                                    # no bitmap
    d += s16("") * 48 + i(0, 0, 0) * 16 + (bytes(16) if v >= 1.20 else b"") + i(-99)
    d += (i(200, 200, 200, 100, 100, 0) if v >= 1.17 else i(200, 200, 200, 100)) * 16 + i(-99)
    d += i(1, 0, 0, 0, 0, 0) + i(0, 4, 900, 9000) + i(3) * 256 + bytes(16 * 12 * 60) + i(-99) + i(0) * 16
    d += (i(0) * 16 + i(-1) * 480 + i(0) * 16 + i(-1) * 480 + i(0) * 16 + i(-1) * 320 if v >= 1.18 else i(-1) * 320)
    d += i(0, 0, 0) + i(-1) * 16 + i(-99) + (i(-1, -1) if v >= 1.19 else b"")
    w, h = terrain.shape
    d += struct.pack("<II", w, h)
    d += np.stack([terrain.T, elevation.T.astype(np.int8).view(np.uint8), np.zeros((h, w))], -1).astype(np.uint8).tobytes()
    world = (200, 200, 100, 200, 100, 0) + ((75,) if fmt >= b"1.20" else ())  # population from 1.20, as CAMELOT.SCN (#3964)
    d += struct.pack("<I", 9) + struct.pack(f"<{len(world)}f", *world) * 8
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
    header = struct.pack("<II", 2, 0) + struct.pack("<I", 0) + i(0, 2)
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    with open(path, "wb") as f:
        f.write(fmt + struct.pack("<I", len(header)) + header + c.compress(d) + c.flush())
    return path


@pytest.mark.parametrize("fmt", sorted(DATA))
def test_read_each_format(tmp_path, fmt):
    terrain = np.arange(12, dtype=np.int16).reshape(4, 3)
    elevation = np.array([[0, 1, 2], [0, 0, 1], [3, 0, 0], [0, 0, 7]], np.float32)
    path = build(tmp_path / "old.scn", fmt, terrain, elevation, {1: (4, 1, (2.5, 1.5)), 2: (1, 0, (-1, -1))},
                 objects=[(1, 2.5, 1.5, 83), (0, 1.5, 0.5, 399)])
    s = scx.read(path)
    assert (s["format"], s["width"], s["height"]) == (fmt.decode(), 4, 3)
    assert (s["terrain"] == terrain).all() and (s["elevation"] == elevation).all()
    assert s["players"][1] == {"civ": scx.CIVS[4], "color": 1, "view": (2.5, 1.5)}
    assert s["players"][2] == {"civ": "BRITONS", "color": 0, "view": None}
    assert [(o["player"], o["type"], o["x"], o["y"]) for o in s["objects"]] == [(0, 399, 1.5, 0.5), (1, 83, 2.5, 1.5)]


def test_convert_a_scn(tmp_path):
    import contextlib
    import io

    import aoe2mc
    terrain = np.zeros((16, 16), np.int16)
    terrain[12:, :] = 22
    path = build(tmp_path / "old.scn", b"1.20", terrain, np.zeros((16, 16), np.float32), {1: (1, 1, (6.0, 6.0))},
                 objects=[(1, 6.0, 6.0, 109), (1, 9.5, 4.5, 83), (0, 2.5, 12.5, 399)])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(str(path), str(tmp_path / "W"))
    text = out.getvalue()
    assert "player 1: britons, red, western buildings" in text and "units in a block (moved up): 0" in text
    assert (tmp_path / "W" / "level.dat").exists()
