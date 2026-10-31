"""make_indestructible, set_gaia_unconvertible, set_facet and avoid_actor of create_object in a random map script (#5074)."""
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
<OBJECTS_GENERATION>
"""


def run(objs, seed=1):
    return rmap.generate(LAND + objs, seed, players=2, size=100, warn=lambda m: pytest.fail(m))["objects"]


def test_flags():
    objs = run("create_object SHEEP { number_of_objects 2 make_indestructible set_gaia_unconvertible set_facet 3 }\n"
               "create_object RELIC { number_of_objects 1 }")
    sheep = [o for o in objs if o["name"] == "SHEEP"]
    relic = [o for o in objs if o["name"] == "RELIC"]
    assert len(sheep) == 2 and all(o.get("indestructible") and o.get("unconvertible") for o in sheep)
    assert "indestructible" not in relic[0] and "unconvertible" not in relic[0]
    assert all("facet" not in o for o in objs)         # set_facet: no effect in Minecraft


@pytest.mark.parametrize("seed", range(1, 4))
def test_avoid_actor(seed):
    objs = run("create_object RELIC { number_of_objects 2 actor_area 5 actor_area_radius 4 }\n"
               "create_object STONE { number_of_objects 6 avoid_actor 5 }", seed)
    relic = [o for o in objs if o["name"] == "RELIC"]
    stone = [o for o in objs if o["name"] == "STONE_MINE"]
    assert len(relic) == 2 and len(stone) == 6
    assert not any(max(abs(s["x"] - r["x"]), abs(s["y"] - r["y"])) <= 4 for s in stone for r in relic)


def test_read_json_keeps_flags(tmp_path):
    import json

    import aoe2mc
    d = {"size": 8, "terrain": [[0] * 8] * 8, "objects": [{"name": "SHEEP", "x": 2, "y": 2, "indestructible": True, "unconvertible": True},
                                {"name": "SHEEP", "x": 4, "y": 4}]}
    p = tmp_path / "m.json"
    p.write_text(json.dumps(d))
    objs = aoe2mc.read_json(str(p))[5]
    assert objs[0]["indestructible"] and objs[0]["unconvertible"] and "indestructible" not in objs[1]
