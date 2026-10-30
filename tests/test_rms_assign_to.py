"""assign_to of create_land (#4424): the land of a player, of the player of a color, or of a player of a team."""
import rmap

PLAYER = """<PLAYER_SETUP>
direct_placement
<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT assign_to AT_PLAYER 2 0 0 land_position 80 20 base_size 5 }
create_land { terrain_type DIRT assign_to AT_COLOR 1 0 0 land_position 20 70 base_size 5 }
"""
TEAM = """<PLAYER_SETUP>
direct_placement
<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT assign_to AT_TEAM 1 0 0 land_position 20 20 base_size 4 }
create_land { terrain_type DIRT assign_to AT_TEAM -1 0 0 land_position 80 80 base_size 4 }
"""


def lands(text, players=2, teams=None):
    warns = []
    d = rmap.generate(text, 1, players, size=100, warn=warns.append, teams=teams)
    return {st["player"]: (st["x"], st["y"]) for st in d["lands"]}, warns


def test_assign_to_player_and_color_put_the_starts_at_the_land_positions():
    at, warns = lands(PLAYER)
    assert abs(at[2][0] - 80) <= 5 and abs(at[2][1] - 20) <= 5
    assert abs(at[1][0] - 20) <= 5 and abs(at[1][1] - 70) <= 5
    assert not [w for w in warns if "assign_to" in w or "no land" in w]


def test_assign_to_team_gives_the_land_to_a_player_of_the_team():
    at, warns = lands(TEAM, 4, [2, 1, 2, 1])
    assert at[2] == (20, 20) and at[1] == (80, 80)       # team 1: player 2; any team: the next free player, 1
    assert not [w for w in warns if "assign_to" in w]
