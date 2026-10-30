"""set_zone_by_team of create_player_lands: the lands of a team share one zone (#4696)."""
import numpy as np
import pytest
from test_rms_connections import reach

import rmap

TEXT = """<PLAYER_SETUP>
grouped_by_team
<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS land_percent 10 base_size 3 set_zone_by_team }
<CONNECTION_GENERATION>
create_connect_same_land_zones { replace_terrain WATER SHALLOW }
"""


def test_the_lands_of_a_team_share_one_zone():
    d = rmap.generate(TEXT, 3, players=4, size=100, teams=[1, 1, 2, 2], warn=lambda m: pytest.fail(m))
    t = np.array(d["terrain"]) != rmap.TERRAINS["WATER"]
    at = {st["player"]: (st["x"], st["y"]) for st in d["lands"]}
    seen = reach(t, at[1])
    assert at[2] in seen and at[3] not in seen and at[4] not in seen
    assert at[4] in reach(t, at[3])
