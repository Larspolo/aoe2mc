"""The name tables of the converter are one JSON line each in data/*.jsonl (#1917): units.ANIMALS, units.LINES and
buildings.FOOTPRINT; the object tables of aoe2mc.py, buildings.py and scx.py (#2036)."""
import json
import os

import nbtlib

import buildings
import units

KEYS = {"animals.jsonl": ({"keys", "behavior", "mob"}, {"tags", "note"}),
        "carriers.jsonl": ({"name", "garrison"}, set()),
        "tech_names.jsonl": ({"tech", "name"}, set()),
        "trigger_conditions.jsonl": ({"name", "text"}, set()),
        "trigger_effects.jsonl": ({"name", "text"}, set()),
        "looks.jsonl": ({"name", "pattern", "accent"}, {"crest"}),
        "sounds.jsonl": ({"name", "sound"}, set()),
        "designs.jsonl": ({"name", "design"}, {"args", "wall"}),
        "objects.jsonl": ({"name"}, {"decor", "map_color", "mob", "monument", "no_blocks", "obstacle", "passable", "rocks"}),
        "old_ids.jsonl": ({"id", "name"}, set()),
        "scx_civs.jsonl": ({"id", "name"}, set()),
        "train.jsonl": ({"name", "seconds", "building"}, set()),
        "work_sounds.jsonl": ({"name", "sound", "when", "particle"}, set()),
        "rmap.jsonl": ({"name"}, {"cliff_type", "fish", "forest", "object", "scatter", "shore_fish", "start", "terrain", "wolves"}),
        "lines.jsonl": ({"name", "mob", "armor", "main", "off"}, {"tags"}),
        "footprint.jsonl": ({"name", "size"}, set()),
        "weapons.jsonl": ({"name", "weapon"}, set()),
        "units.jsonl": ({"name"}, {"base", "bird", "crew", "drop", "flying", "hero", "infantry", "invisible", "joke",
                                   "plain", "ruler", "tags", "tier"})}


def test_each_line_has_its_keys():
    assert sorted(os.listdir(units.DATA)) == sorted(KEYS), \
        "give each data/*.jsonl file its line in KEYS: put a new line after the animals.jsonl line, not at the end (#2072)"
    for name, (need, may) in KEYS.items():
        for line in open(os.path.join(units.DATA, name), encoding="utf-8"):
            row = json.loads(line)
            assert need <= set(row) <= need | may, (name, row)
            if "tags" in row:
                assert isinstance(nbtlib.parse_nbt(row["tags"]), nbtlib.Compound), row["tags"]


def test_the_tables_come_from_the_files():
    assert units.ANIMALS[0] == (("ALFRED_THE_ALPACA",), "military", "llama", {"Variant": nbtlib.Int(1)})
    bear = next(tags for keys, *_, tags in units.ANIMALS if keys == ("POLAR_BEAR",))
    assert type(bear["anger_end_time"]) is nbtlib.Long
    assert units.LINES["EAGLE_SCOUT"] == ("husk", (("leather", 0xC89B3C), None, None, None), "wooden_sword", None)
    assert type(units.LINES["KARAMBIT_WARRIOR"][4]["IsBaby"]) is nbtlib.Byte
    assert units.LINES["HUSKARL_BARRACKS"] == units.LINES["HUSKARL"]
    assert buildings.FOOTPRINT[0] == ("SHIPYARD", 4) and len({w for w, _ in buildings.FOOTPRINT}) == len(buildings.FOOTPRINT)


def test_the_first_match_wins():
    assert units.animal("ARCTIC_WOLF") != units.animal("WOLF")              # the ARCTIC_WOLF line comes before WOLF
    assert buildings.footprint("GREAT_PYRAMID") != buildings.footprint("PYRAMID")
