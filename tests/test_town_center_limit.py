"""game/build.py locked: a second town center needs the Castle Age, the Cumans the Feudal Age, as in AoE2 DE (#1951)."""
import types

from game import build, combat

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [4, 8, 4, 8]}


def player(objects=(TC,), ages=0, civ="BRITONS", sites=(), standing=True):
    """A Gather of player 1 whose server answers "passed" for the target of a standing town center."""
    sent = []

    def command(cmd):
        sent.append(cmd)
        return "Test passed, count: 1" if standing else "Test failed"
    return types.SimpleNamespace(player=1, sites=list(sites), techs=set(build.AGE_TECHS[:ages]), command=command,
                                 sent=sent, data={"objects": list(objects), "players": {"1": {"civ": civ}}})


def test_a_second_town_center_in_the_dark_age_needs_the_castle_age():
    g = player()
    assert build.locked(g, "TOWN_CENTER") == "Needs the Castle Age"
    assert g.sent == [f"execute if entity {combat.target_uuid(TC['footprint'])}"]
    assert build.locked(player(ages=1), "TOWN_CENTER") == "Needs the Castle Age"


def test_with_no_town_center_or_a_destroyed_one_the_town_center_is_free():
    assert build.locked(player(objects=()), "TOWN_CENTER") is None
    assert build.locked(player(standing=False), "TOWN_CENTER") is None


def test_in_the_castle_age_a_second_town_center_is_free():
    g = player(ages=2)
    assert build.locked(g, "TOWN_CENTER") is None and g.sent == []


def test_the_cumans_build_a_second_town_center_in_the_feudal_age():
    assert build.locked(player(civ="CUMANS", ages=1), "TOWN_CENTER") is None
    assert build.locked(player(civ="CUMANS"), "TOWN_CENTER") == "Needs the Castle Age"


def test_a_town_center_site_counts_also_before_it_is_complete():
    site = {"name": "TOWN_CENTER", "player": 1, "footprint": [4, 8, 4, 8], "progress": 0.2}
    g = player(objects=(), sites=[site], standing=False)
    assert build.locked(g, "TOWN_CENTER") == "Needs the Castle Age" and g.sent == []
    assert build.locked(player(objects=(), sites=[site | {"done": True}], standing=False), "TOWN_CENTER") is None
