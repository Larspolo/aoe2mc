"""rmap.py: the commands of <PLAYER_SETUP> (#4580)."""
import pytest

import rmap


def run(text, **kw):
    notes = []
    return rmap.generate(text, 1, warn=notes.append, **kw), notes


def test_override_map_size_in_player_setup_sets_the_size():
    m, notes = run("<PLAYER_SETUP>\noverride_map_size 144\n<LAND_GENERATION>\nbase_terrain GRASS", players=8)
    assert m["size"] == 144 and len(m["terrain"]) == 144 and notes == []


def test_a_size_of_the_caller_wins_over_override_map_size_in_player_setup():
    m, _ = run("<PLAYER_SETUP>\noverride_map_size 144\n<LAND_GENERATION>\nbase_terrain GRASS", size=100)
    assert m["size"] == 100


@pytest.mark.parametrize("cmd", sorted(rmap.PLAYER_SETUP))
def test_a_command_of_player_setup_that_is_read_gives_no_warning(cmd):
    arg = "144" if cmd == "override_map_size" else "1"
    _, notes = run(f"<PLAYER_SETUP>\n{cmd} {arg}\n<LAND_GENERATION>\nbase_terrain GRASS")
    assert notes == []


def test_an_unknown_command_of_player_setup_gives_one_warning():
    _, notes = run("<PLAYER_SETUP>\nfoo_bar 1\n<LAND_GENERATION>\nbase_terrain GRASS")
    assert notes == ["foo_bar is not read yet"]
