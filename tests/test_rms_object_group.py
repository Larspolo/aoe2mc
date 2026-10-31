"""create_object_group NAME { add_object TYPE PERCENT } makes a pool that create_object NAME places: each object of the
pool with the same chance, as in AoE2 DE (aoe2-rms docs: "the % currently doesn't work", #5251)."""
import collections

import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
<OBJECTS_GENERATION>
create_object_group HERD
{
  add_object SHEEP 90
  add_object DEER 10
  add_object NOT_AN_OBJECT 50
}
create_object HERD
{
  number_of_objects 60
  enable_tile_shuffling
}
create_object_group EMPTY
{
  add_object NOT_AN_OBJECT 100
}
create_object EMPTY { number_of_objects 3 }
"""


def make(seed):
    notes = []
    return rmap.generate(SCRIPT, seed, 2, warn=notes.append), notes


def names(m):
    return collections.Counter(o["name"] for o in m["objects"])


def test_create_object_places_the_objects_of_its_group():
    m, notes = make(4)
    count = names(m)
    assert set(count) == {"SHEEP", "DEER"} and sum(count.values()) == 60
    assert min(count.values()) >= 15                    # the same chance for each: the percent has no effect
    assert not [n for n in notes if "not read yet" in n or "HERD" in n]


def test_an_unknown_object_of_a_group_is_skipped_with_one_warning():
    _, notes = make(4)
    assert [n for n in notes if "NOT_AN_OBJECT" in n] == ["constant NOT_AN_OBJECT is not defined: the command or attribute is skipped"]
    assert "create_object EMPTY: the group has no known object" in notes


def test_a_group_gives_the_same_map_for_the_same_seed():
    (a, _), (b, _) = make(7), make(7)
    assert a["objects"] == b["objects"]
