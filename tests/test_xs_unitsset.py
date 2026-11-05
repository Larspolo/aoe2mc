"""The XS functions that make, change and order a unit (game/xs_host.py, #5841): each one gives the command of the
trigger effect that does the same, on the fake side of tests/test_xs_unitsread.py."""
from types import SimpleNamespace as NS

import ai
import combat
import owners
import scenario
import train

from game import xs_host
from game.xs_run import Xs
from tests.test_xs_host import ARCHER
from tests.test_xs_unitsread import HOUSE, game


def run(g, body, typ="bool"):
    x = Xs(f"{typ} r = {'false' if typ == 'bool' else 0}; void main() {{ {body} }}", out=print, host=xs_host.host(g))
    x.tick(0)
    return x.get("r")


def fake():
    g = game()
    g.map, g.players = NS(T=4, y=lambda x, z: 64), {"1": {}, "2": {}}
    return g


def test_create_unit_summons_it_and_gives_the_next_id(monkeypatch):
    g, made = fake(), []

    def summon(x, name, pos, *a, **k):
        made.append((x.player, name, pos))
        x.soldiers["n-1"] = name
        return "n-1"
    monkeypatch.setattr(train, "summon", summon)
    assert run(g, f"r = xsCreateUnit({ARCHER}, 1, vector(3, 5, 0));", "int") == 22   # above the militia (21)
    assert made == [(1, "ARCHER", (12.5, 64.0, 20.5))]
    assert run(g, f"r = xsCreateUnit({ARCHER}, 1, vector(-1, -1, -1));", "int") == -1


def test_create_building_places_a_foundation(monkeypatch):
    g, made = fake(), []
    monkeypatch.setattr(scenario, "foundation", lambda x, p, n, tile, done: made.append((p, n, tile, done)))
    house = next(i for i, (_, n) in xs_host.aoe2mc.object_kinds().items() if n == "HOUSE")
    run(g, f"xsCreateUnit({house}, 1, vector(4, 6, 0), true);", "int")
    assert made == [(1, "HOUSE", (4, 6), False)]


def test_remove_and_hitpoints_and_name():
    g = fake()
    assert run(g, "r = xsRemoveUnit(7);")
    assert run(g, "r = xsSetUnitHitpoints(7, 12.5);") and run(g, "r = xsSetUnitHitpoints(3, 100.0);")
    assert run(g, 'r = xsSetUnitName(7, "Hero");')
    assert {"kill a-1", "data modify entity a-1 Health set value 12.5f",
            f"scoreboard players set {combat.target_uuid(HOUSE)} aoe_hp 100",
            'data modify entity a-1 CustomName set value "Hero"'} <= set(g.commands)
    assert not run(g, "r = xsRemoveUnit(3);")                          # a building: no form
    assert not run(g, "r = xsRemoveUnit(999);")                        # an unknown id


def test_owner_position_flash(monkeypatch):
    g, given = fake(), []
    monkeypatch.setattr(owners, "give", lambda x, uuid, new: given.append((uuid, new)))
    assert run(g, "r = xsSetUnitOwner(7, 2);") and given == [("a-1", 2)]
    assert not run(g, "r = xsSetUnitOwner(7, 5);")                     # no player 5
    assert run(g, "r = xsSetUnitPosition(7, vector(2, 3, 0));") and run(g, "r = xsFlashUnit(7);")
    assert {"team join p2 a-1", "tp a-1 8.5 64.0 12.5", "effect give a-1 minecraft:glowing 2 0 true"} <= set(g.commands)


def test_task_and_stop(monkeypatch):
    g, moves, attacks = fake(), [], []
    monkeypatch.setattr(ai, "move", lambda x, uuid, name, T, *p: moves.append((uuid, p)))
    monkeypatch.setattr(ai, "attack", lambda x, uuids, names, T, target: attacks.append((uuids, target)) or [""])
    assert run(g, "r = xsTaskUnits(7, -1, vector(1, 2, 0));") and run(g, "r = xsTaskUnits(7, -1, vector(-1, -1, -1), 21);")
    assert run(g, "r = xsStopUnit(7);")
    assert moves == [("a-1", (4.5, 64.0, 8.5)), ("a-1", (10.0, 64.0, 22.0))] and attacks == [(["a-1"], "e-1")]


def test_held_build_points_gather_point_train(monkeypatch):
    g, rallied, queued = fake(), [], []
    g.sites = [{"footprint": [8, 16, 8, 16], "progress": 0.2, "player": 1, "name": "HOUSE"}]
    monkeypatch.setattr(train, "rally", lambda x, rect, cell: rallied.append((rect, cell)))
    monkeypatch.setattr(train, "queue", lambda x, p, cell, name: queued.append((cell, name)) or (1,))
    assert run(g, "r = xsSetUnitAttributeHeld(9, 7.0, 1);")
    assert (g.villagers["v-1"].res, g.villagers["v-1"].load) == (xs_host.aoe2mc.STORES[1], 7)
    assert run(g, "r = xsSetUnitBuildPoints(3, 0.75);") and g.sites[0]["progress"] == 0.75
    assert run(g, "r = xsSetUnitGatherPoint(3, vector(5, 1, 0));") and rallied == [((8, 16, 8, 16), (20, 4))]
    assert run(g, f"r = xsTrainObject(3, {ARCHER}, 2);") and queued == [((8, 8), "ARCHER")] * 2
