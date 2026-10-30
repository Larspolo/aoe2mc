"""border_fuzziness of the lands of a random map script (#4422): a low value lets a land grow past its borders."""
import numpy as np

import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
create_land {{ terrain_type DIRT land_position 45 50 number_of_tiles 1500 left_border 40 clumping_factor 0 {extra} }}
"""


def dirt(extra, seed=1):
    warns = []
    d = rmap.generate(SCRIPT.format(extra=extra), seed, 2, size=100, warn=warns.append)
    return np.array(d["terrain"]), warns


def left(terrain):
    return int((terrain[:40] == terrain[45, 50]).sum())


def test_fuzziness_100_keeps_the_land_in_its_border():
    terrain, warns = dirt("border_fuzziness 100")
    assert left(terrain) == 0 and not [w for w in warns if "border_fuzziness" in w]


def test_fuzziness_0_lets_the_land_past_its_border():
    terrain, warns = dirt("border_fuzziness 0")
    assert left(terrain) > 0 and not [w for w in warns if "border_fuzziness" in w]


def test_the_same_map_for_the_same_seed():
    a, _ = dirt("border_fuzziness 10", seed=3)
    b, _ = dirt("border_fuzziness 10", seed=3)
    assert (a == b).all()
