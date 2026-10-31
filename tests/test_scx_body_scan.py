"""A base scenario with unknown header fields reads its body at the first full deflate stream (#5211)."""
import struct

import numpy as np
from test_scx import build

import scx


def test_unknown_header_fields_are_skipped(tmp_path):
    terrain = np.arange(12, dtype=np.int16).reshape(4, 3)
    elevation = np.zeros((4, 3), np.float32)
    path = build(tmp_path / "old.scx", terrain, elevation, {1: (1, 1, (2.5, 1.5))}, objects=[(1, 2.5, 1.5, 83)])
    data = path.read_bytes()
    size = struct.unpack_from("<I", data, 4)[0]
    # A header length that does not count 12 extra bytes of a newer header version.
    extra = data[:8 + size] + bytes(12) + data[8 + size:]
    new = tmp_path / "de.scx"
    new.write_bytes(extra)
    old, got = scx.read(path), scx.read(new)
    assert np.array_equal(got["terrain"], old["terrain"])
    assert got["objects"] == old["objects"]
