"""An undefined constant in math reads as 0 with one warning (#5068): the DE includes define PLAYERn_ALLY_COUNT only
for the players in the game, and Manchuria uses MAPSCALE_SIDE with no scaling.inc."""
import rmap

INCLUDE = "if PLAYER1_TEAM0\n#const PLAYER1_ALLY_COUNT 0\nendif\n#const ENEMIES (PLAYER_COUNT - PLAYER3_ALLY_COUNT - 1)\n"
SCRIPT = ("#include_drs includes/helpers.inc\n#const SIDE (MAPSCALE_SIDE + 1)\n<LAND_GENERATION>\nbase_terrain GRASS\n"
          "if PLAYER1_TEAM0\nbase_terrain (ENEMIES + SIDE + PLAYER1_ALLY_COUNT)\nendif\n")


def test_an_undefined_constant_in_math_is_0_with_one_warning(tmp_path):
    (tmp_path / "includes").mkdir()
    (tmp_path / "includes" / "helpers.inc").write_text(INCLUDE + INCLUDE)
    notes = []
    m = rmap.generate(SCRIPT, 1, players=2, size=40, warn=notes.append, folder=str(tmp_path))
    assert {m["terrain"][0][0]} == {2}              # ENEMIES 1 + SIDE 1 + ALLY 0: terrain 2
    assert sorted(n for n in notes if "not defined" in n) == [
        "constant MAPSCALE_SIDE is not defined, read as 0 in math",
        "constant PLAYER3_ALLY_COUNT is not defined, read as 0 in math"]
    assert not [n for n in notes if "is not read" in n]
