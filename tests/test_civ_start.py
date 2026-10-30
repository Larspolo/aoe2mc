"""game/civs.py: each player starts with the start resources of the own civilization (AoE2 DE bonuses, #1269)."""
from test_gather import FakeServer, grid

from game import civs, gather, train

UNITS = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [1.5, 1.5]}]
TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [4.0, 4.0], "footprint": [2, 2, 6, 6]}


def stock(civ, objects=UNITS + [TC], **kw):
    data = grid([[64] * 8 for _ in range(8)], objects)
    data["players"] = {"1": {"civ": civ, "color": 0}}
    return gather.Gather(FakeServer({}), data, **kw).stock


BASE = next(r["name"] for r in civs.ROWS if r["name"] not in civs.START)   # a civilization with no bonus


def plus(civ, base):
    return {r: max(0, v + civs.START.get(civ, {}).get(r, 0)) for r, v in base.items()}


def test_each_civilization_starts_with_its_bonus():
    for civ in sorted(civs.START):
        assert stock(civ) == plus(civ, gather.START), civ


def test_a_civilization_with_no_bonus_starts_with_the_aoe2_start():
    assert stock(BASE) == stock(None) == gather.START


def test_the_bonus_adds_to_a_nomad_start_and_start_wins():
    assert stock("PERSIANS", UNITS) == plus("PERSIANS", stock(BASE, UNITS))
    assert stock("PERSIANS", start={})["wood"] == 0                                  # start= is not changed


def test_each_entry_is_a_known_civilization_and_resource():
    assert list(civs.START) == sorted(civs.START) and set(civs.START) <= set(train.UNIQUE)
    assert all(set(b) <= set(gather.START) and all(b.values()) for b in civs.START.values())
