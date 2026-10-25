"""Garrisoned units stand next to their holder or ride their ship (#21)."""
import contextlib
import io
from collections import Counter

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from test_terrain import columns

import aoe2mc
import buildings
import scenarios
import world_reader


def garrison_map(path):
    """A town center with 3 garrisoned villagers and 1 villager outside."""
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    tc = um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=8, y=8)
    for _ in range(3):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8, y=8, garrisoned_in_id=tc.reference_id)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_FEMALE.ID, x=3.5, y=3.5)
    return scenarios.save(scn, path)


def convert(src, out, **kw):
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        aoe2mc.convert(src, out, **kw)
    return world_reader.World(out), log.getvalue().splitlines()


def villagers(w):
    return [e for e in w.entities() if "Villager" in str(e.get("CustomName", ""))]


def test_garrisoned_units_stand_next_to_the_holder(tmp_path):
    src = garrison_map(str(tmp_path / "g.aoe2scenario"))
    w, log = convert(src, str(tmp_path / "W"))
    assert "  units in a block (moved up): 0" in log
    assert "  units (garrisoned, next to the holder): 3" in log
    vs = villagers(w)
    assert len(vs) == 4
    half = buildings.footprint("TOWN_CENTER") * 4 / 2
    cols = set()
    for e in vs:
        x, _, z = (float(v) for v in e["Pos"])
        cols.add((int(x), int(z)))
        if abs(x - 14) > 4:                              # not the free villager at (3.5, 3.5) tiles
            assert max(abs(x - 32), abs(z - 32)) >= half       # outside the footprint
            assert max(abs(x - 32), abs(z - 32)) <= half + 4   # but next to it
    assert len(cols) == 4                                # each in its own column

    w, log = convert(src, str(tmp_path / "S"), garrison="skip")
    assert "  units (garrisoned, skipped): 3" in log
    assert len(villagers(w)) == 1


def test_garrisoned_units_ride_a_ship_with_a_free_seat():
    cols = columns([[1] * 8] * 8)
    o = dict(kind="U", player=1, x=4, y=4, rotation=0.0, hero=False, garrisoned=False, holder=None)
    objects = [dict(o, name="FISHING_SHIP", ref=1), dict(o, name="TRANSPORT_SHIP", ref=2)]
    objects += [dict(o, name="ARCHER", ref=10 + i, garrisoned=True, holder=1 + i % 2) for i in range(4)]
    stats = Counter()
    out = aoe2mc.plan_units(objects, {}, cols, aoe2mc.np.random.default_rng(1), stats)
    ships = [nbt for ents in out.values() for nbt, *_ in ents]
    assert len(ships) == 2
    seats = {str(s["id"]): len(s["Passengers"]) for s in ships}
    assert seats == {"minecraft:boat": 2, "minecraft:chest_boat": 1}   # the fishing ship had one free seat
    assert stats["units (garrisoned, in a ship)"] == 1
    assert stats["units (garrisoned, no free seat in the ship, skipped)"] == 3
