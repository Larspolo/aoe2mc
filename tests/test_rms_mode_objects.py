"""--game-mode places the objects of the mode of a random map (#5200): the King of each player in Regicide, the
Monument at the center in King of the Hill."""
import rmap

SCRIPT = """<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain GRASS
create_player_lands
{
  terrain_type GRASS
  land_percent 50
  base_size 6
}
<OBJECTS_GENERATION>
if REGICIDE
create_object KING
{
  set_place_for_every_player
  min_distance_to_players 4
  max_distance_to_players 6
}
endif
if KING_OT_HILL
create_object MONUMENT
{
  max_distance_to_players 0
}
endif
"""


def made(mode, seed=3, script=SCRIPT):
    warns = []
    d = rmap.generate(script, seed, players=2, size=60, warn=warns.append, mode=mode)
    assert warns == []
    return d


def named(d, name):
    return [o for o in d["objects"] if o["name"] == name]


def test_regicide_gives_one_king_per_player():
    assert sorted(o["player"] for o in named(made("regicide"), "KING")) == [1, 2]
    assert named(made("standard"), "KING") == []


def test_king_of_the_hill_gives_the_monument_at_the_center():
    d = made("king-of-the-hill")
    assert [(o["x"], o["y"]) for o in named(d, "MONUMENT")] == [(d["size"] / 2, d["size"] / 2)]
    assert named(made("standard"), "MONUMENT") == []


def test_king_of_the_hill_adds_the_monument_of_the_game():
    d = made("king-of-the-hill", script=SCRIPT.split("<OBJECTS_GENERATION>")[0])
    assert len(named(d, "MONUMENT")) == 1


def test_the_same_seed_gives_the_same_objects():
    assert made("regicide")["objects"] == made("regicide")["objects"]
