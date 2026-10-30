"""resource_delta of create_object (#4429): the objects carry the delta, and gather adds it to the amount of a mine."""
import rmap
from test_gather import FakeServer, grid

from game import gather

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
<OBJECTS_GENERATION>
create_object GOLD { number_of_objects 2 resource_delta 100 }
"""


def test_the_objects_of_create_object_carry_the_delta():
    warns = []
    d = rmap.generate(SCRIPT, 1, 2, size=40, warn=warns.append)
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert len(gold) == 2 and all(o["resource_delta"] == 100 for o in gold)
    assert not [w for w in warns if "resource_delta" in w]


def test_the_amount_of_a_mine_is_the_default_plus_the_delta():
    objects = [{"kind": "other", "name": "GOLD_MINE", "tile": [5.5, 5.5], "resource_delta": 100},
               {"kind": "other", "name": "GOLD_MINE", "tile": [12.5, 12.5]}]
    g = gather.Gather(FakeServer({}), grid([[64] * 24 for _ in range(24)], objects), carry=10, chop=0.25, start={}).setup()
    gold = gather.MINES["GOLD_MINE"][1]
    assert g.map.mines["gold"] == {(5, 5): gold + 100, (12, 12): gold}
