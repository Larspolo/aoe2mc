"""The versioned map of the HD Edition scenarios (marker 0xDEADF00D, genie-scx map.rs, #3861)."""
import struct

import numpy as np
import pytest

import scx

W, H = 5, 3
TERRAIN = np.arange(W * H, dtype=np.uint8).reshape(H, W) % 40       # rows of y, then x
ELEV = (np.arange(W * H).reshape(H, W) % 4).astype(np.int8)


def map_part(version):
    """The bytes of a map part of the version (None: format 1.21, no marker), then a marker of the next part."""
    out = b"" if version is None else struct.pack("<II", 0xDEADF00D, version) + b"\x01" * (version >= 2)
    out += struct.pack("<II", W, H)
    for y in range(H):
        for x in range(W):
            out += struct.pack("<Bbb", TERRAIN[y, x], ELEV[y, x], 0)
            if version and version >= 1:
                out += struct.pack("<HH", 0xFFFF, 7)                # mask type, layered terrain
    return out + b"NEXT"


@pytest.mark.parametrize("version", [None, 0, 1, 2])
def test_each_map_version_gives_size_terrain_and_elevation(version):
    s = scx.Stream(map_part(version))
    terrain, elevation = scx.read_map(s, "x.scx")
    assert terrain.shape == (W, H) and (terrain == TERRAIN.T).all() and (elevation == ELEV.T).all()
    assert s.take(4) == b"NEXT"                                     # the reader is at the end of the map


def test_an_unknown_map_version_names_it():
    with pytest.raises(scx.ScxError, match="map version 9"):
        scx.read_map(scx.Stream(map_part(2).replace(struct.pack("<I", 2), struct.pack("<I", 9), 1)), "x.scx")
