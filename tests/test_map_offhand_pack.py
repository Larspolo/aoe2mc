"""The datapack holds the map pulse (#966) also when the world has no work sound, ambience, team, trigger or fog
(#3034). Only --ambience off writes no pack. Fake world, no server."""
import os

import numpy as np

import aoe2mc


def test_a_house_alone_writes_the_map_pulse(tmp_path):
    ground = np.full((32, 32), 70)
    house = {"kind": "B", "name": "HOUSE", "footprint": [4, 4, 12, 12]}
    assert aoe2mc.write_datapack(str(tmp_path), [house], ground) == (0, 0)
    with open(os.path.join(tmp_path, "datapacks", "aoe2mc", "data", "aoe2mc", "function", "pulse.mcfunction")) as f:
        lines = f.read().splitlines()
    assert all(ln in lines for ln in aoe2mc.MAP_PULSE)


def test_the_pack_is_written_unless_the_ambience_is_off(tmp_path):
    ground = np.full((32, 32), 70)
    aoe2mc.write_datapack(str(tmp_path / "basic"), [], ground, ambience="basic")
    assert os.path.exists(tmp_path / "basic" / "datapacks" / "aoe2mc" / "pack.mcmeta")
    aoe2mc.write_datapack(str(tmp_path / "off"), [], ground, ambience="off")
    assert not os.path.exists(tmp_path / "off" / "datapacks")
