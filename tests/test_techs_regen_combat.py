"""The keys "combat_regen" (Ordo Cavalry) and "building_regen" (Fortified Bastions, #4334): units regenerate a share of
their max hit points near an enemy, own buildings of a list regain hit points (civs.regen, regen.buildings). Test data:
monkeypatched train.BY_KEY lines, not the menu or the values of the data lines (owner, #4242)."""
import pytest
import train as plain_train  # civs and regen import train by its plain name (not game.train)
from test_gather import grid
from test_repair import HpServer
from test_train_castle import setup

from game import civs, combat, gather, regen, repair, train

HOUSE, CASTLE = (4, 6, 4, 6), (12, 16, 12, 16)                     # block footprints (x0, x1, z0, z1)


def test_a_combat_technology_regenerates_a_share_of_the_max_hit_points_near_an_enemy(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["combat_regen"], "TEST_TECH", ["cavalry but archers", 1.5, 2])
    server, g = setup("KHITANS", ages=3)
    knight, archer = (("KNIGHT", combat.stats("KNIGHT")), ("CAVALRY_ARCHER", combat.stats("CAVALRY_ARCHER")))
    base = {n: (civs.regen(g, n, s, 1.0), civs.regen(g, n, s, 9.0)) for n, s in (knight, archer)}
    g.techs.add("TEST_TECH")
    assert civs.regen(g, *knight, 1.0) == pytest.approx(base["KNIGHT"][0] + 1.5 * knight[1].hp)
    assert civs.regen(g, *knight, 9.0) == base["KNIGHT"][1]                     # far from enemies
    assert civs.regen(g, *archer, 1.0) == base["CAVALRY_ARCHER"][0]             # not in the group


def bastion_map():
    objects = [{"kind": "building", "name": "HOUSE", "player": 1, "tile": [5, 5], "footprint": [4, 4, 6, 6]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [14, 14], "footprint": [12, 12, 16, 16]}]
    server = HpServer({}, {repair.uuid(HOUSE): 100, repair.uuid(CASTLE): 1000})
    return server, gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()


def test_a_building_technology_heals_the_buildings_of_its_list(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["building_regen"], "TEST_TECH", {"buildings": ["CASTLE"], "rate": 500})
    for m in (train, plain_train):                                  # build.values applies each researched technology
        monkeypatch.setitem(m.TECHS, "TEST_TECH", lambda n, s: s)
    server, g = bastion_map()
    regen.tick(g, 60.0)
    assert server.hp == {repair.uuid(HOUSE): 100, repair.uuid(CASTLE): 1000}   # no research
    g.techs.add("TEST_TECH")
    regen.tick(g, 60.0)                                                         # one AoE2 minute
    assert server.hp == {repair.uuid(HOUSE): 100, repair.uuid(CASTLE): 1500}
    server.hp[repair.uuid(CASTLE)] = (top := repair.full(g, "CASTLE", 1, CASTLE)) - 10
    regen.tick(g, 60.0)
    assert server.hp[repair.uuid(CASTLE)] == top                                # never more than the full hit points
