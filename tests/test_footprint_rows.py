"""Each AoE2 building has a footprint line in data/footprint.jsonl (#3092)."""
import buildings
from AoE2ScenarioParser.datasets.buildings import BuildingInfo


def test_each_building_matches_a_footprint_line():
    missing = [b.name for b in BuildingInfo if not any(word in b.name for word, _ in buildings.FOOTPRINT)]
    assert missing == []


def test_keep_is_one_tile_like_the_towers():
    assert buildings.footprint("KEEP") == buildings.footprint("GUARD_TOWER") == 1


def test_big_and_small_sizes_from_the_wiki():
    assert buildings.footprint("FORTRESS") == 4
    assert buildings.footprint("WOODEN_FORT") == 4
    assert buildings.footprint("SHRINE") == 3
    assert buildings.footprint("MACEDONIAN_COMMAND_POST") == 3
    assert buildings.footprint("STORAGE") == 2
    assert buildings.footprint("BARRICADE_C") == 2
    assert buildings.footprint("TENT_B") == 2


def test_old_lines_keep_their_size():
    assert buildings.footprint("PAGAN_SHRINE") == 3
    assert buildings.footprint("ARMY_TENT_A") == 2
    assert buildings.footprint("GREEK_COMMANDER_TENT") == 2
