"""The part after the map of a special_map_* base scenario of format 1.35 (#5316): the bytes of the owner's dump of
special_map_yinyang (#5209, #5316). Each scenario player has 115 bytes; the "ff ff ff ff" at its end is the last field
of the victory data of version 2.0, not an extra i32. The test puts that part after the map of a small own file."""
import struct
import zlib

import scx
from tests.test_scenario_de_135 import ELEVATION, TERRAIN, build

# One scenario player of the dump: name, view, location, allied victory, diplomacy, unit diplomacy, color, victory data
PLAYER = bytes.fromhex(
    "1800 5363656e6172696f20456469746f72205068616e746f6d00 728354 43f440c741 6e006e00 00 0900 030003030303030303"
    "00000000 01000000 04000000 04000000 04000000 04000000 04000000 04000000 04000000 00000000 00000040"
    "00000000 00 00000000 00000000 00000000 ffffffff")


def obj(k, x, y, kind):
    return struct.pack("<fffiHBfhi", x, y, 0, k, kind, 2, 4, 0, -1)


def tail():
    """World player data, scenario player data and objects as in the dump; then the start of the triggers."""
    d = struct.pack("<I", 9) + struct.pack("<7f", 200, 200, 100, 100, 100, 0, 75) * 8
    d += struct.pack("<I", 9) + PLAYER * 8
    d += struct.pack("<I", 8) + b"".join(obj(k, 1.5 + k % 4, 1.5 + k // 4, 709) for k in range(8))   # GAIA: 8 trees
    d += b"".join(struct.pack("<I", 1) + obj(8 + p, 2.5, 3.5, 109) for p in range(1, 9))          # 1 town center each
    return d + struct.pack("<d", 2.2) + bytes(1024)


def test_the_special_map_part_after_the_map_reads_to_the_objects(tmp_path):
    assert len(PLAYER) == 115
    path = build(tmp_path / "special_map_x.scx", "1.35", TERRAIN, ELEVATION, {p: p for p in range(1, 9)}, [])
    data = path.read_bytes()
    start = scx.body_start(data)
    s = scx.Stream(scx.inflate(data, start))
    s.i32()
    scx.tribe_scen(s)
    scx.read_map(s, path)
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    path.write_bytes(data[:start] + c.compress(s.data[:s.pos] + tail()) + c.flush())

    r = scx.read(path)
    assert [(o["player"], o["type"]) for o in r["objects"]] == [(0, 709)] * 8 + [(p, 109) for p in range(1, 9)]
    assert sorted(r["players"]) == list(range(9))
    assert r["players"][1]["color"] == 0 and round(r["players"][1]["view"][0], 1) == 212.5
