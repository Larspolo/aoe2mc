"""The player and team labels of a random map script: N_PLAYER_GAME, N_TEAM_GAME, TEAMn_SIZEm, PLAYERn_TEAMm (#5008)."""
import numpy as np

import rmap

LABELS = ("4_PLAYER_GAME", "2_PLAYER_GAME", "2_TEAM_GAME", "0_TEAM_GAME", "TEAM1_SIZE2", "PLAYER3_TEAM2",
          "PLAYER3_TEAM1", "PLAYER1_TEAM0")
SCRIPT = "<LAND_GENERATION>\nbase_terrain GRASS\n" + "".join(
    f"if {label}\nbase_terrain {terrain}\nendif\n" for label, terrain in (
        ("4_PLAYER_GAME", "DESERT"), ("2_PLAYER_GAME", "SNOW"), ("2_TEAM_GAME", "BEACH"),
        ("0_TEAM_GAME", "DIRT"), ("TEAM1_SIZE2", "JUNGLE"), ("PLAYER3_TEAM2", "WATER"),
        ("PLAYER3_TEAM1", "FOREST"), ("PLAYER1_TEAM0", "ROCK")))


def active(players, teams):
    """The labels of the script that its if blocks read as defined, for this lobby."""
    defined = rmap.team_labels(players, teams)
    return {label for label in LABELS if label in defined}


def terrain(**kw):
    return int(np.array(rmap.generate(SCRIPT, 3, warn=lambda m: None, **kw)["terrain"])[0, 0])


def test_teams_give_the_player_and_team_labels():
    assert active(4, [1, 1, 2, 2]) == {"4_PLAYER_GAME", "2_TEAM_GAME", "TEAM1_SIZE2", "PLAYER3_TEAM2"}


def test_no_teams_give_team_0_and_no_team_labels():
    assert active(4, None) == {"4_PLAYER_GAME", "0_TEAM_GAME", "PLAYER1_TEAM0"}


def test_a_player_with_no_team_is_in_team_0():
    assert "PLAYER2_TEAM0" in rmap.team_labels(2, [1, None])
    assert "1_TEAM_GAME" in rmap.team_labels(2, [1, None])


def test_generate_reads_the_team_labels():
    # each active block sets the terrain: the last active one wins (PLAYER3_TEAM2, PLAYER1_TEAM0)
    assert terrain(players=4, teams=[1, 1, 2, 2]) == rmap.TERRAINS["WATER"]
    assert terrain(players=2, teams=None) == rmap.TERRAINS["ROCK"]
