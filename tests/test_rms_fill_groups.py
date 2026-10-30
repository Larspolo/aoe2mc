"""A create_object command that asks for more groups than fit places those that fit; it warns only with no group (#4721)."""
import rmap

LAND = "<LAND_GENERATION>\nbase_terrain GRASS\n<OBJECTS_GENERATION>\n"


def run(objs):
    warns = []
    d = rmap.generate(LAND + objs, 1, players=2, size=120, warn=warns.append)
    return [o for o in d["objects"] if o["name"] == "RELIC"], warns


def test_fill_groups_no_warning():
    relic, warns = run("create_object RELIC { number_of_objects 1 number_of_groups 150 temp_min_distance_group_placement 40 }")
    assert 1 < len(relic) < 150
    assert not [w for w in warns if "no free tile" in w]


def test_no_group_warns():
    relic, warns = run("create_object RELIC { number_of_objects 1 number_of_groups 3 terrain_to_place_on WATER }")
    assert not relic
    assert [w for w in warns if "no free tile" in w]
