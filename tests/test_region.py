"""write_region writes chunks larger than 1 MiB to external .mcc files, and world_reader reads them back."""
import io

import nbtlib
import numpy as np
import world_reader

import aoe2mc


def nbt_bytes(compound):
    buf = io.BytesIO()
    nbtlib.File(compound).write(buf)
    return buf.getvalue()


def test_large_chunk_goes_to_mcc(tmp_path):
    noise = np.random.default_rng(0).integers(0, 256, 1_200_000, dtype=np.uint8).tobytes()   # not compressible
    big = nbtlib.Compound({"xPos": nbtlib.Int(33), "Noise": nbtlib.ByteArray(np.frombuffer(noise, np.int8))})
    small = nbtlib.Compound({"xPos": nbtlib.Int(32)})
    path = tmp_path / "r.1.-1.mca"
    aoe2mc.write_region(str(path), {(1, 2): nbt_bytes(big), (0, 0): nbt_bytes(small)})
    assert (tmp_path / "c.33.-30.mcc").exists()          # chunk x = 32 + 1, z = -32 + 2
    assert path.stat().st_size == 4 * 4096                # header (2 sectors) + one sector per chunk
    chunks = world_reader.read_region(str(path))
    assert int(chunks[(0, 0)]["xPos"]) == 32
    assert bytes(np.asarray(chunks[(1, 2)]["Noise"], np.int8).tobytes()) == noise
