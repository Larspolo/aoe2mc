"""game/civs.py: each player starts with the start resources of the own civilization (AoE2 DE bonuses, #1269)."""
from game import civs, gather, train

from test_gather import FakeServer, grid

UNITS = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [1.5, 1.5]}]
TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [4.0, 4.0], "footprint": [2, 2, 6, 6]}


def stock(civ, objects=UNITS + [TC], **kw):
    data = grid([[64] * 8 for _ in range(8)], objects)
    data["players"] = {"1": {"civ": civ, "color": 0}}
    return gather.Gather(FakeServer({}), data, **kw).stock


def test_persians_start_with_50_more_food_and_wood():
    # AoE2 wiki, "Persians": "Start the game with +50 food, +50 wood"
    assert stock("PERSIANS") == {**gather.START, "food": 250, "wood": 250}


def test_more_start_bonuses():
    assert stock("AZTECS")["gold"] == 150 and stock("SICILIANS")["stone"] == 300
    assert stock("CHINESE")["food"] == 0 and stock("CHINESE")["wood"] == 150
    assert stock("HUNS")["wood"] == 100 and stock("LITHUANIANS")["food"] == 300 and stock("MAYANS")["food"] == 150


def test_a_civilization_with_no_bonus_starts_with_the_aoe2_start():
    assert stock("GOTHS") == stock(None) == gather.START


def test_the_bonus_adds_to_a_nomad_start_and_start_wins():
    assert stock("PERSIANS", UNITS) == {"wood": 525, "food": 250, "gold": 100, "stone": 300}
    assert stock("PERSIANS", start={})["wood"] == 0                                  # start= is not changed


def test_each_entry_is_a_known_civilization_and_resource():
    assert list(civs.START) == sorted(civs.START) and set(civs.START) <= set(train.UNIQUE)
    assert all(set(b) <= set(gather.START) and all(b.values()) for b in civs.START.values())
