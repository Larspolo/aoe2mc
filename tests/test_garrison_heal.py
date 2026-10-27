"""game/garrison.py: an injured unit in a garrison gets its hit points back, 0.2 per AoE2 second in a castle and 0.1 in
a town center or tower, up to max_health (AoE2 wiki "Garrison", #1262). Siege units and ships do not heal."""
import pytest
from test_gather import grid
from test_monk_heal import HealServer

from game import garrison, gather

TC, CASTLE = (2, 6, 2, 6), (10, 16, 10, 16)                       # block footprints (x0, x1, z0, z1)


def setup(*inside):
    """A flat 24 × 24 map (tile size 1) with an own town center and castle, and the units of `inside`:
    (uuid, name, building, health, max)."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [4, 4], "footprint": [2, 2, 6, 6]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [13, 13], "footprint": [10, 10, 16, 16]}]
    ents = {}
    for uuid, name, rect, hp, top in inside:
        objects.append({"kind": "unit", "name": name, "player": 1, "uuid": uuid, "tile": [20.5, 20.5]})
        ents[uuid] = {"Pos": (rect[0] + 1.5, 64.0, rect[2] + 1.5), "Health": hp, "Max": top}
    server = HealServer(ents)
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    for uuid, name, rect, hp, top in inside:
        g.soldiers[uuid] = name
        g.garrisons.setdefault(rect, []).append(uuid)
    return server, g


def run(g, seconds):
    for _ in range(round(seconds / garrison.HEAL_EVERY)):
        garrison.heal(g, garrison.HEAL_EVERY)


def test_a_castle_heals_0_2_and_a_town_center_0_1_hit_points_per_second_up_to_max_health():
    server, g = setup(("a", "MILITIA", CASTLE, 10.0, 40.0), ("b", "MILITIA", TC, 10.0, 40.0))
    run(g, 50)
    assert server.entities["a"]["Health"] == pytest.approx(20.0) and server.entities["b"]["Health"] == pytest.approx(15.0)
    run(g, 300)
    assert server.entities["a"]["Health"] == 40.0 and server.entities["b"]["Health"] == 40.0


def test_no_heal_for_siege_units_ships_and_units_outside():
    server, g = setup(("ram", "BATTERING_RAM", CASTLE, 10.0, 175.0), ("ship", "GALLEY", CASTLE, 10.0, 120.0))
    server.entities["out"] = {"Pos": (20.5, 64.0, 20.5), "Health": 10.0, "Max": 40.0}
    g.soldiers["out"] = "MILITIA"
    run(g, 50)
    assert [e["Health"] for e in server.entities.values()] == [10.0] * 3


def test_a_full_unit_is_read_once_and_again_after_it_left():
    server, g = setup(("a", "MILITIA", CASTLE, 40.0, 40.0))
    run(g, 20)
    assert sum(c == "data get entity a Health" for c in server.log) == 1 and g.whole == {"a"}
    g.garrisons[CASTLE] = []
    run(g, 5)
    assert g.whole == set()                                        # it left
    server.entities["a"]["Health"] = 30.0
    g.garrisons[CASTLE] = ["a"]
    run(g, 5)
    assert server.entities["a"]["Health"] == 31.0                   # it came back injured: read again


def test_the_step_calls_the_heal_in_aoe2_seconds():
    server, g = setup(("a", "MILITIA", CASTLE, 10.0, 40.0))
    for _ in range(80):                                                # 20 real seconds at Normal speed
        g.step()
    assert server.entities["a"]["Health"] == pytest.approx(10 + 0.2 * 20 * gather.NORMAL, abs=0.2 * garrison.HEAL_EVERY)
