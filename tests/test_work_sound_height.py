"""The work sound of a building plays at the ground next to it, not on its roof (#588)."""
import os

import numpy as np

import aoe2mc

PULSE = os.path.join("datapacks", "aoe2mc", "data", "aoe2mc", "function", "pulse.mcfunction")


def pulse(tmp_path, objects, ground):
    aoe2mc.write_datapack(str(tmp_path), objects, ground)
    with open(tmp_path / PULSE) as f:
        return [line for line in f if "playsound" in line]


def test_the_sound_plays_at_the_ground_next_to_the_building(tmp_path):
    ground = np.full((32, 32), 64, np.int16)
    ground[8:16, 8:16] = 80                                   # the roof of the mill: "ground" in the footprint
    ground[16, 8:16] = 66                                     # a step on one side: the median stays 64
    mill = {"kind": "B", "name": "MILL", "footprint": [8, 8, 16, 16]}
    line, = pulse(tmp_path, [mill], ground)
    assert line.startswith("execute positioned 12 64 12 if entity @a[distance=..16] ")


def test_the_check_is_not_larger_than_the_hearing_distance(tmp_path):
    ground = np.full((16, 16), 70, np.int16)
    mill = {"kind": "B", "name": "MILL", "footprint": [0, 0, 4, 4]}  # at the edge of the map
    line, = pulse(tmp_path, [mill], ground)
    assert " 2 70 2 " in line and "distance=..16]" in line and " ambient @a ~ ~ ~ 1 " in line
