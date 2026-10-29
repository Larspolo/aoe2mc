"""The key "trickle" of game/data/train.jsonl (#4279): each working unit of a kind adds income after the research.
Test data only (owner, 2026-10-29, #4242)."""
from test_train_castle import setup

import pytest
import train as plain_train          # feitoria imports train by its plain name
from game import feitoria, gather

RATE = 0.02


def crew(g, who):
    """Three units of kind who and one idle villager; the stock starts at 0."""
    farm, tree = (0, 0), (5, 5)
    g.map.farms[farm], g.map.trees[tree] = 100, 100
    g.villagers.clear()
    g.soldiers.clear()
    for k in range(3):
        if who == "military":
            g.soldiers[f"s{k}"] = "MILITIA"
        else:
            v = g.villagers[f"v{k}"] = gather.Villager(f"v{k}", (1.0, 64.0, 1.0))
            v.state, v.tree, v.res = "chop", farm if who == "farm" else tree, "food" if who == "farm" else "wood"
    g.villagers["idle"] = gather.Villager("idle", (1.0, 64.0, 1.0))
    g.stock.update(food=0, wood=0, gold=0, stone=0)


@pytest.mark.parametrize("who", ["farm", "wood", "military"])
@pytest.mark.parametrize("researched", [True, False])
def test_each_working_unit_adds_the_rate(monkeypatch, who, researched):
    monkeypatch.setattr(feitoria, "RATE", {})
    monkeypatch.setitem(plain_train.BY_KEY["trickle"], "TEST_TECH", [who, {"gold": RATE}])
    server, g = setup("BRITONS")
    crew(g, who)
    if researched:
        g.techs.add("TEST_TECH")
    for _ in range(100):
        feitoria.tick(g, 1.0)
    assert g.stock["gold"] == (int(RATE * 3 * 100 + 1e-9) if researched else 0)


def test_other_villagers_add_nothing(monkeypatch):
    monkeypatch.setattr(feitoria, "RATE", {})
    monkeypatch.setitem(plain_train.BY_KEY["trickle"], "TEST_TECH", ["wood", {"gold": RATE}])
    server, g = setup("BRITONS")
    crew(g, "farm")                                                  # farmers, not lumberjacks
    g.techs.add("TEST_TECH")
    for _ in range(100):
        feitoria.tick(g, 1.0)
    assert g.stock["gold"] == 0
