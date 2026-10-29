"""direct_placement of a random map (#3947): create_land with assign_to_player or assign_to_team is a player land."""
import rmap

DIRECT = """<PLAYER_SETUP>
direct_placement
<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT assign_to_player 2 land_position 80 20 base_size 5 }
create_land { terrain_type DIRT assign_to_player 1 land_position 20 70 base_size 5 }
"""
TEAM = """<PLAYER_SETUP>
direct_placement
<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT assign_to_team 1 land_position 20 20 base_size 4 }
create_land { terrain_type DIRT assign_to_team 1 land_position 80 80 base_size 4 }
"""


def lands(text, players=2, teams=None):
    warns = []
    d = rmap.generate(text, 1, players, size=100, warn=warns.append, teams=teams)
    return {st["player"]: (st["x"], st["y"]) for st in d["lands"]}, warns


def test_assign_to_player_puts_the_starts_at_the_land_positions():
    at, warns = lands(DIRECT)
    assert abs(at[2][0] - 80) <= 5 and abs(at[2][1] - 20) <= 5
    assert abs(at[1][0] - 20) <= 5 and abs(at[1][1] - 70) <= 5
    assert not [w for w in warns if "assign_to" in w or "no land" in w]


def test_assign_to_team_gives_the_lands_to_the_players_of_the_team():
    at, warns = lands(TEAM, 4, [1, 2, 1, 2])
    assert at[1] == (20, 20) and at[3] == (80, 80)
    assert {2, 4} <= set(at) and sum("no land" in w for w in warns) == 2   # the rest on the circle, with a warning
