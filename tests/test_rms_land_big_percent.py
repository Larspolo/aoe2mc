"""A land with borders and a land_percent larger than its borders (#5423, Hideout): its origin is inside its borders,
so the land fills the area in its borders.

The rule: in AoE2 DE a land starts at a random origin inside its borders and grows until it has its land_percent or
no tile is free (the RMS guide of Zetnus, the land borders: the border area gets neither the land origin nor
the land, except by border_fuzziness). Before #5423 the origin was drawn on all of the map: a land with an origin outside its
borders took no tile."""
import numpy as np

import rmap

SCRIPT = """<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 16 base_size 8 clumping_factor 15 }
create_land { terrain_type FOREST land_percent 90 top_border 20 bottom_border 20 left_border 20 right_border 20
  clumping_factor 15 border_fuzziness 45 zone 52 other_zone_avoidance_distance 0 }
"""


def share(seed):
    """The part of the tiles in the borders (20 to 80 of 100) and not of a player land that the forest takes."""
    t = np.array(rmap.generate(SCRIPT, seed, 4, size=100, warn=lambda w: None)["terrain"])[20:80, 20:80]
    return (t == rmap.TERRAINS["FOREST"]).sum() / (t != rmap.TERRAINS["DIRT"]).sum()


def test_the_big_land_fills_the_area_in_its_borders():
    for seed in (1, 2, 3, 4):
        assert share(seed) > 0.9, seed
