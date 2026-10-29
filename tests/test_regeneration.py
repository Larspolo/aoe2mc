"""game/regen.py: Polish villagers, Georgian mounted units, Wu infantry and Thracian elite skirmishers regenerate hit
points at the rates of the data (civs.REGEN, #2247)."""
import math

import pytest
from test_gather import grid
from test_monk_heal import HealServer

from game import civs, combat, gather, regen

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


def rate(g, name, foe=math.inf):
    """The hit points per AoE2 minute of unit name in the data (civs.regen)."""
    return civs.regen(g, name, combat.stats(name), foe)


def after(g, name, hp, top, seconds=60, foe=math.inf):
    """The health of unit name after seconds of regeneration."""
    return pytest.approx(min(top, hp + rate(g, name, foe) * seconds / 60), abs=0.01)


@pytest.mark.parametrize("age", [1, 2, 3])
def test_a_polish_villager_regenerates_up_to_its_maximum(age):
    server, g = setup("POLES", age, ("v", "VILLAGER_MALE", 5.0, 25.0))
    assert "v" in g.villagers
    run(g, 60)
    assert server.entities["v"]["Health"] == after(g, "VILLAGER_MALE", 5.0, 25.0) != 5.0
    run(g, 6000)
    assert server.entities["v"]["Health"] == 25.0


def test_georgian_mounted_units_and_wu_infantry_regenerate_at_their_rates():
    server, g = setup("GEORGIANS", 2, ("k", "KNIGHT", 50.0, 100.0), ("m", "MAN_AT_ARMS", 20.0, 45.0))
    run(g, 60)
    assert server.entities["k"]["Health"] == after(g, "KNIGHT", 50.0, 100.0) != 50.0
    assert server.entities["m"]["Health"] == after(g, "MAN_AT_ARMS", 20.0, 45.0)
    server, g = setup("WU", 3, ("k", "KNIGHT", 50.0, 100.0), ("m", "MAN_AT_ARMS", 10.0, 45.0))
    run(g, 60)
    assert server.entities["k"]["Health"] == after(g, "KNIGHT", 50.0, 100.0)
    assert server.entities["m"]["Health"] == after(g, "MAN_AT_ARMS", 10.0, 45.0) != 10.0


def test_thracian_skirmishers_regenerate_at_their_rates():
    units = ("a", "SKIRMISHER", 10.0, 30.0), ("b", "ELITE_SKIRMISHER", 10.0, 35.0), ("c", "IMPERIAL_SKIRMISHER", 10.0, 35.0)
    server, g = setup("THRACIANS", 3, *units)
    run(g, 60)
    assert [server.entities[u]["Health"] for u, *_ in units] == [after(g, n, h, t) for _, n, h, t in units]
    assert server.entities["c"]["Health"] != 10.0


def test_the_dark_age_rate_and_no_regeneration_for_other_civilizations():
    server, g = setup("POLES", 0, ("v", "VILLAGER_MALE", 5.0, 25.0))
    run(g, 60)
    assert server.entities["v"]["Health"] == after(g, "VILLAGER_MALE", 5.0, 25.0)
    server, g = setup("FRANKS", 3, ("v", "VILLAGER_MALE", 5.0, 25.0), ("m", "MAN_AT_ARMS", 20.0, 45.0))
    run(g, 60)
    assert [e["Health"] for e in server.entities.values()] == [5.0, 20.0]
    assert not [c for c in server.log if "Health" in c]           # no command for a civilization without the bonus


def test_the_step_calls_the_regeneration_in_aoe2_seconds():
    server, g = setup("WU", 3, ("m", "MAN_AT_ARMS", 20.0, 45.0))
    for _ in range(80):                                                # 20 real seconds at Normal speed
        g.step()
    r = rate(g, "MAN_AT_ARMS") / 60                                    # hit points per AoE2 second
    assert server.entities["m"]["Health"] == pytest.approx(min(45.0, 20 + r * 20 * gather.NORMAL), abs=r * regen.EVERY)
