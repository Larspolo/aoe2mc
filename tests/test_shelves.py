"""Shelves with goods in the market and tools in the blacksmith (#526)."""
import mcvalid
import render

import aoe2mc
import buildings


def shelves(name, arch="western"):
    buildings.SHELVES.clear()
    xs, ys, zs, states = render.building_blocks(name, arch)
    return {p: s for p, s in zip(zip(xs.tolist(), ys.tolist(), zs.tolist()), states) if "_shelf[" in s}


def test_market_and_blacksmith_have_shelves_with_three_items():
    for name, sample in (("MARKET", "bread"), ("BLACKSMITH", "iron_sword")):
        found = shelves(name)
        assert len(found) >= 3 and set(found) == set(buildings.SHELVES)
        assert all(mcvalid.block_error(s) is None and aoe2mc.block_entity_type(s) == "shelf" for s in found.values())
        assert all(len(v) == 3 for v in buildings.SHELVES.values())
        assert any(sample in v for v in buildings.SHELVES.values())


def test_shelf_wood_follows_the_style_and_other_buildings_have_no_items():
    assert any(s.startswith("minecraft:spruce_shelf") for s in shelves("MARKET").values())
    assert shelves("HOUSE") == {} and buildings.SHELVES == {}
    assert aoe2mc.block_entity_type("minecraft:bookshelf") is None


def test_shelf_data_fills_the_three_slots():
    items = aoe2mc.shelf_data(("wheat", "bread", "apple"))["Items"]
    assert [(int(i["Slot"]), str(i["id"]), int(i["count"])) for i in items] == \
        [(0, "minecraft:wheat", 1), (1, "minecraft:bread", 1), (2, "minecraft:apple", 1)]
