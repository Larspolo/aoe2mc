"""Each AoE2 building has a footprint line in data/footprint.jsonl (#3092)."""
from AoE2ScenarioParser.datasets.buildings import BuildingInfo

import buildings


def test_each_building_matches_a_footprint_line():
    missing = [b.name for b in BuildingInfo if not any(word in b.name for word, _ in buildings.FOOTPRINT)]
    assert missing == []

