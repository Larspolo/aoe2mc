"""The object tables of aoe2mc.py, buildings.py and scx.py come from data/*.jsonl (#2036): the form of the lines and
the rules that read them. No test copies a value or a count of the files (#2008)."""
import aoe2mc
import buildings
import scx


def test_each_design_line_names_a_design_function():
    for r in buildings.DESIGNS:
        assert callable(getattr(buildings, r["design"], None)), r
        assert isinstance(r.get("args", {}), dict) and r.get("wall", True) is True, r


def test_the_ids_are_unique_and_scx_civs_start_with_gaia():
    old = [r["id"] for r in aoe2mc.units.rows("old_ids.jsonl")]
    assert len(set(old)) == len(old)
    assert [r["id"] for r in aoe2mc.units.rows("scx_civs.jsonl")] == list(range(len(scx.CIVS))) and scx.CIVS[0] == "GAIA"


def test_each_object_name_has_one_line_and_known_keys():
    names = [r["name"] for r in aoe2mc.OBJECTS]
    assert len(set(names)) == len(names)
    decor = {"statue", "stall", "head", "loot", "fence", "pots"}            # the designs of decor() that read the key
    assert all(r.get("decor", "statue") in decor for r in aoe2mc.OBJECTS)
    assert all(isinstance(r.get("map_color", 0), int) for r in aoe2mc.OBJECTS)


def test_the_rules_read_the_lines():
    assert aoe2mc.object_mob("FISH_SALMON") != aoe2mc.object_mob("FISH_PERCH")     # SALMON comes before FISH
    assert buildings.select("BUDDHA_STATUE_A")[1] and not buildings.select("BUDDHA_STATUE")[1]
    assert buildings.is_wall("PALISADE_GATE") and not buildings.is_wall("CASTLE")
    assert aoe2mc.train("ARCHER")[1] == "ARCHERY_RANGE" and aoe2mc.train("COBRA_CAR") is None
