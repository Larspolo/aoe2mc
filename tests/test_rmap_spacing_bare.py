"""spacing_to_other_terrain_types with no number (Moats): no stop, the DE default 0 (#5174)."""
import pytest

import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DESERT land_percent 30 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain DESERT land_percent 10 spacing_to_other_terrain_types%s }
<ELEVATION_GENERATION>
create_elevation 3 { base_terrain GRASS number_of_tiles 300 spacing_to_other_terrain_types%s }
"""


def run(arg, seed=1):
    d = rmap.generate(SCRIPT % (arg, arg), seed, players=2, size=60, warn=lambda m: pytest.fail(m))
    return d["terrain"], d["elevation"]


@pytest.mark.parametrize("seed", [1, 2])
def test_bare_spacing_converts_as_spacing_0_and_is_deterministic(seed):
    assert run("", seed) == run("", seed) == run(" 0", seed)
