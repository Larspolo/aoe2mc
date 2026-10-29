"""An HD scenario with a header length of 0 (version 3, DLC options) reads its body after the header fields (#3847)."""
import struct

import numpy as np

import scx
from test_scx import build


def test_header_length_zero_reads_the_body_after_the_fields(tmp_path):
    terrain = np.arange(12, dtype=np.int16).reshape(4, 3)
    elevation = np.zeros((4, 3), np.float32)
    path = build(tmp_path / "old.scx", terrain, elevation, {1: (1, 1, (2.5, 1.5))}, objects=[(1, 2.5, 1.5, 83)])
    data = path.read_bytes()
    body = data[8 + struct.unpack_from("<I", data, 4)[0]:]

    # The header fields of genie-scx: version 3, time stamp, empty description, any SP victory, active players,
    # DLC options (data set 0, no dependencies). The header length is 0: the body follows the last field.
    header = struct.pack("<IIIIIII", 3, 0, 0, 0, 0, 0, 0)
    hd = tmp_path / "hd.scx"
    hd.write_bytes(b"1.21" + struct.pack("<I", 0) + header + body)

    assert scx.body_start(hd.read_bytes()) == 8 + len(header)
    old, new = scx.read(path), scx.read(hd)
    assert (new["width"], new["height"]) == (4, 3)
    assert np.array_equal(new["terrain"], old["terrain"])
    assert new["objects"] == old["objects"]
