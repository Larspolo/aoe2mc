"""game/regen.py: Polish villagers, Georgian mounted units, Wu infantry and Thracian elite skirmishers regenerate hit
points, as in AoE2 DE (civs.REGEN, #2247)."""
import pytest
from test_gather import grid
from test_monk_heal import HealServer

from game import gather, regen

AGES = ((), ("FEUDAL_AGE",), ("FEUDAL_AGE", "CASTLE_AGE"), ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))


def setup(civ, age, *units):
    """A flat 16 × 16 map with the own units of `units` (uuid, name, health, max) of a player of civ in age 0 ... 3."""
    objects, ents = [], {}
    for i, (uuid, name, hp, top) in enumerate(units):
        objects.append({"kind": "unit", "name": name, "player": 1, "uuid": uuid, "tile": [2.5 + i, 2.5]})
        ents[uuid] = {"Pos": (2.5 + i, 64.0, 2.5), "Health": hp, "Max": top}
    server = HealServer(ents)
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.update(AGES[age])
    for uuid, name, *_ in units:
        if not name.startswith("VILLAGER"):
            g.soldiers[uuid] = name
    return server, g


def run(g, seconds):
    for _ in range(round(seconds / regen.EVERY)):
        regen.tick(g, regen.EVERY)


@pytest.mark.parametrize("age, gain", [(1, 10), (2, 15), (3, 20)])
def test_a_polish_villager_regenerates_10_15_20_hit_points_per_minute_up_to_its_maximum(age, gain):
    server, g = setup("POLES", age, ("v", "VILLAGER_MALE", 5.0, 25.0))
    assert "v" in g.villagers
    run(g, 60)
    assert server.entities["v"]["Health"] == pytest.approx(5 + gain, abs=0.01)
    run(g, 120)
    assert server.entities["v"]["Health"] == 25.0


def test_georgian_mounted_units_and_wu_infantry_regenerate_at_their_rates():
    server, g = setup("GEORGIANS", 2, ("k", "KNIGHT", 50.0, 100.0), ("m", "MAN_AT_ARMS", 20.0, 45.0))
    run(g, 60)
    assert server.entities["k"]["Health"] == pytest.approx(58, abs=0.01) and server.entities["m"]["Health"] == 20.0
    server, g = setup("WU", 3, ("k", "KNIGHT", 50.0, 100.0), ("m", "MAN_AT_ARMS", 10.0, 45.0))
    run(g, 60)
    assert server.entities["k"]["Health"] == 50.0 and server.entities["m"]["Health"] == pytest.approx(40, abs=0.01)


def test_thracian_elite_skirmishers_regenerate_and_the_first_skirmisher_does_not():
    server, g = setup("THRACIANS", 3, ("a", "SKIRMISHER", 10.0, 30.0), ("b", "ELITE_SKIRMISHER", 10.0, 35.0),
                      ("c", "IMPERIAL_SKIRMISHER", 10.0, 35.0))
    run(g, 60)
    assert [server.entities[u]["Health"] for u in "abc"] == pytest.approx([10, 15, 20], abs=0.01)


def test_no_regeneration_in_the_dark_age_and_for_other_civilizations():
    server, g = setup("POLES", 0, ("v", "VILLAGER_MALE", 5.0, 25.0))
    run(g, 60)
    assert server.entities["v"]["Health"] == 5.0
    server, g = setup("FRANKS", 3, ("v", "VILLAGER_MALE", 5.0, 25.0), ("m", "MAN_AT_ARMS", 20.0, 45.0))
    run(g, 60)
    assert [e["Health"] for e in server.entities.values()] == [5.0, 20.0]
    assert not [c for c in server.log if "Health" in c]           # no command for a civilization without the bonus


def test_the_step_calls_the_regeneration_in_aoe2_seconds():
    server, g = setup("WU", 3, ("m", "MAN_AT_ARMS", 20.0, 45.0))
    for _ in range(80):                                                # 20 real seconds at Normal speed
        g.step()
    assert server.entities["m"]["Health"] == pytest.approx(20 + 0.5 * 20 * gather.NORMAL, abs=0.5 * regen.EVERY)
