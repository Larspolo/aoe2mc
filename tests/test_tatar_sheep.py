"""A Tatar town center that is complete in the Castle Age gives two own sheep next to it (#2313, AoE2 DE wiki,
"Tatars"): BUILT_UNITS in game/data/civs.jsonl. Fake server."""
import pytest

from game import build, civs
from test_treadmill_crane import castle


def sheep(civ, age=2, name="TOWN_CENTER"):
    """The game and the commands of the completion of a site of name of civ in age (2: the Castle Age)."""
    server, g = castle(civ)
    g.techs -= set(build.AGE_TECHS[age:])
    site = build.found(g, name, (12, 16, 8, 12))
    before = len(server.log)
    assert build.rise(g, site, build.BUILD_TIMES[name])
    build.rise(g, site, 1.0)                                          # once only
    return g, [c for c in server.log[before:] if c.startswith("summon minecraft:sheep")]


@pytest.mark.parametrize("age", [2, 3])
def test_a_tatar_town_center_gives_two_own_sheep_from_the_castle_age(age):
    g, cmds = sheep("TATARS", age)
    assert len(cmds) == 2
    new = [o for o in g.data["objects"] if o["name"] == "SHEEP" and o["player"] == g.player]
    assert len(new) == 2 and {o["uuid"] for o in new} <= g.flock & g.prey.keys()
    for o in new:                                                      # next to the town center, outside it
        x, z = o["tile"][0] * g.map.T, o["tile"][1] * g.map.T
        assert 11 <= x <= 16 and 7 <= z <= 12 and not (12 <= x < 16 and 8 <= z < 12)


@pytest.mark.parametrize("civ, age, name", [("TATARS", 1, "TOWN_CENTER"), ("BRITONS", 2, "TOWN_CENTER"),
                                            ("TATARS", 2, "HOUSE")])
def test_no_sheep_in_the_feudal_age_for_other_civilizations_or_buildings(civ, age, name):
    assert sheep(civ, age, name)[1] == []


def test_the_names_are_buildings():
    assert {n for b in civs.BUILT_UNITS.values() for n in b} <= set(build.BUILD_TIMES)
