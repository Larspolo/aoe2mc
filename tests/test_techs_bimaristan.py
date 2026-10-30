"""A technology with the key "unit_aura" (Bimaristan, #4366): the own monks heal the allied land units near them
(regen.units). Test data: a monkeypatched train.BY_KEY line, not the values of the data line (owner, #4242)."""
import pytest
import train as plain_train  # regen imports train by its plain name (not game.train)
from test_gather import grid
from test_monk_heal import HealServer

from game import gather, regen

TECH = "TEST_UNIT_AURA"


def heal_map(monkeypatch):
    """A flat 40 × 40 map (tile size 1): two own monks, a hurt own militia 3 tiles from one, a militia 8 tiles away,
    a militia near both monks and an enemy militia near a monk."""
    monkeypatch.setitem(plain_train.BY_KEY["unit_aura"], TECH,
                        {"from": "monks", "group": "land units but siege", "range": 5, "rate": 60})
    units = (("monk", "MONK", 1, 10.5, 10.5), ("near", "MILITIA", 1, 13.5, 10.5), ("far", "MILITIA", 1, 18.5, 10.5),
             ("monk2", "MONK", 1, 30.5, 30.5), ("both", "MILITIA", 1, 30.5, 32.5), ("foe", "MILITIA", 2, 10.5, 12.5))
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [x, z]} for u, n, p, x, z in units]
    objects.append({"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk3", "tile": [31.5, 30.5]})
    pos = {u: (x, z) for u, _, _, x, z in units} | {"monk3": (31.5, 30.5)}
    server = HealServer({u: {"Pos": (x, 64.0, z), "Health": 10.0, "Max": 100.0} for u, (x, z) in pos.items()})
    data = grid([[64] * 40 for _ in range(40)], objects)
    data["players"] = {"1": {"civ": "SARACENS"}, "2": {"civ": "BRITONS"}}
    return server, gather.Gather(server, data).setup()


def hp(server):
    return {u: e["Health"] for u, e in server.entities.items()}


def test_monks_heal_land_units_near_them_after_the_research(monkeypatch):
    server, g = heal_map(monkeypatch)
    g.techs.add(TECH)
    regen.tick(g, 60.0)                                                # one AoE2 minute
    h = hp(server)
    assert h["near"] == h["both"] == pytest.approx(10.0 + 60)          # two monks: the rate once
    assert h["far"] == h["foe"] == 10.0                                # 8 tiles away, an enemy
    assert h["monk"] == 10.0                                           # a monk alone: not itself
    assert h["monk2"] == pytest.approx(70.0)                           # a monk near another monk


def test_no_research_heals_nothing(monkeypatch):
    server, g = heal_map(monkeypatch)
    regen.tick(g, 60.0)
    assert all(v == 10.0 for v in hp(server).values())
