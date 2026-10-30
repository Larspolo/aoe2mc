"""An .aoe2scenario of the HD Edition (formats 1.22 to 1.26) goes to read_scx, not to read_scenario (#3862)."""
import contextlib
import io
import struct
import zlib

import numpy as np
import pytest
from test_scx import build

import aoe2mc
import scx


def hd_file(path, fmt):
    """A file of build() with the format fmt and the versioned map of HD (marker 0xDEADF00D, map version 2)."""
    terrain = np.zeros((16, 16), np.int16)
    terrain[12:, :] = 22                                                     # deep water in the east
    elevation = np.zeros((16, 16), np.float32)
    elevation[:3, :3] = 1
    build(path, terrain, elevation, {1: (1, 1, (6.0, 6.0)), 2: (15, 3, (10.0, 10.0))},
          objects=[(1, 6.0, 6.0, 109), (1, 9.5, 4.5, 83), (0, 2.5, 12.5, 399)], fmt=fmt)
    data = path.read_bytes()
    header = struct.unpack_from("<I", data, 4)[0]
    body = zlib.decompress(data[8 + header:], -15)
    old = struct.pack("<II", 16, 16)
    tiles = np.stack([terrain.T, elevation.T.astype(np.int8).view(np.uint8), np.zeros((16, 16))], -1).astype(np.uint8)
    new = (struct.pack("<II", 0xDEADF00D, 2) + b"\0" + old +
           np.concatenate([tiles, np.full((16, 16, 4), 0xFF, np.uint8)], -1).tobytes())   # mask type, layer: none
    i = body.index(old + tiles.tobytes())
    body = body[:i] + new + body[i + len(old) + tiles.nbytes:]
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    path.write_bytes(data[:8 + header] + c.compress(body) + c.flush())
    return path, terrain


@pytest.mark.parametrize("fmt", [b"1.22", b"1.26"])
def test_an_hd_scenario_converts(tmp_path, fmt):
    path, terrain = hd_file(tmp_path / "hd.aoe2scenario", fmt)
    assert aoe2mc.old_format(str(path))
    s = scx.read(path)
    assert (s["format"], s["width"], s["height"]) == (fmt.decode(), 16, 16) and (s["terrain"] == terrain).all()
    assert set(s["players"]) == {0, 1, 2} and s["players"][2]["civ"] == scx.CIVS[15]
    assert sorted(o["type"] for o in s["objects"]) == [83, 109, 399]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(str(path), str(tmp_path / "W"))
    text = out.getvalue()
    assert f"player 1: {scx.CIVS[1].lower()}, red" in text
    assert "units in a block (moved up): 0" in text


def test_a_de_scenario_goes_to_read_scenario(tmp_path):
    import scenarios
    path = tmp_path / "de.aoe2scenario"
    scenarios.tiny(str(path))
    assert not aoe2mc.old_format(str(path))
    assert path.read_bytes()[:4] not in scx.FORMATS
