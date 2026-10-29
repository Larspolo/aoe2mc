"""rmap.py: a command before the first section of a random map script (#4308)."""
import rmap


def run(text, **kw):
    notes = []
    return rmap.generate(text, 1, warn=notes.append, **kw), notes


def test_a_command_before_the_first_section_gives_a_map_and_one_warning():
    m, notes = run("ai_info_map_type ARABIA 0 0 0\n<LAND_GENERATION>\nbase_terrain GRASS")
    assert m["size"] == rmap.SIZES[2] and len(m["terrain"]) == m["size"]
    assert notes == ["ai_info_map_type is not read yet"]


def test_override_map_size_sets_the_size():
    m, notes = run("override_map_size 144\n<LAND_GENERATION>\nbase_terrain GRASS", players=8)
    assert m["size"] == 144 and len(m["terrain"]) == 144 and notes == []
    assert run("override_map_size 144\n<LAND_GENERATION>\nbase_terrain GRASS", size=100)[0]["size"] == 100
