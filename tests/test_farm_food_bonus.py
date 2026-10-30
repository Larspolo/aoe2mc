"""game/gather.py: a new own farm gets the key farm_food of its civilization on top of FARM_FOOD (the Sumerians, #4444).
The key is a test value (monkeypatch), not the data. Fake server, no Minecraft."""
from test_gather import grid

from game import gather


def farm(civ):
    """The food of a new own farm of a player of civ."""
    data = grid([[64] * 4 + ["-"] * 8 for _ in range(12)])
    data["players"] = {"1": {"civ": civ}}
    return gather.Map(data, 1).farm_food


def test_a_civilization_with_farm_food_gets_more_food_per_new_farm(monkeypatch):
    monkeypatch.setitem(gather.civs.BY_KEY["farm_food"], "TEST", 125)   # the module that gather reads
    assert farm("TEST") == gather.FARM_FOOD + 125
    assert farm("BRITONS") == gather.FARM_FOOD
