"""The XS unit ids and the functions that read a unit (game/xs_host.py, #5837): a start object keeps its scenario
reference ID, a new one takes the next ID, and the state comes from the entity."""
import re
from types import SimpleNamespace as NS

import combat
import gather
import record

import aoe2mc
from game import xs_host
from game.xs_run import Xs
from tests.test_xs_host import side

ARCHER = next(i for i, (_, n) in aoe2mc.object_kinds().items() if n == "ARCHER")
HOUSE = [8, 8, 16, 16]                                                 # block footprint [x0, z0, x1, z1]


def game():
    g = side()
    g.data = {"objects": [{"kind": "unit", "name": "ARCHER", "player": 1, "uuid": "a-1", "ref": 7},
                          {"kind": "unit", "name": "VILLAGER_FEMALE", "player": 1, "uuid": "v-1", "ref": 9},
                          {"kind": "building", "name": "HOUSE", "player": 1, "footprint": HOUSE, "ref": 3},
                          {"kind": "unit", "name": "DEER", "player": 0, "uuid": "d-1", "ref": 20}],
              "players": {"1": {"civ": "BRITONS"}, "2": {"civ": "AZTECS"}}}
    g.soldiers = {"a-1": "ARCHER"}
    g.units = [{"kind": "unit", "name": "VILLAGER_FEMALE", "player": 1, "uuid": "v-1"}]
    g.villagers = {"v-1": gather.Villager("v-1", (0.0, 0.0, 0.0))}
    g.map = NS(T=4)
    g.pos = {"a-1": (10.0, 64.0, 22.0)}.get
    g.positions = lambda us: {u: p for u in us if (p := g.pos(u))}
    enemy = side(2)
    enemy.data, enemy.soldiers, enemy.villagers, enemy.forts = g.data, {"e-1": "MILITIA"}, {}, set()
    g.bots, g.forts = [NS(g=enemy)], {combat.target_uuid(HOUSE)}
    command = g.command

    def answer(cmd):
        if cmd == "data get entity a-1 Health":
            return "a-1 has the following entity data: 25.0f"
        if m := re.fullmatch(r"scoreboard players get (\S+) aoe_hp", cmd):
            return f"{m[1]} has 550 [aoe_hp]"
        return command(cmd)
    g.command = answer
    return g


def value(g, expr, typ="int"):
    init = {"string": '""', "vector": "vector(0, 0, 0)"}.get(typ, "0")
    x = Xs(f"{typ} r = {init}; void main() {{ r = {expr}; }}", out=print, host=xs_host.host(g))
    x.tick(0)
    return x.get("r")


def test_a_start_object_keeps_its_reference_id_and_a_new_one_takes_the_next():
    g = game()
    assert value(g, "xsGetUnitObjectId(7)") == ARCHER
    assert value(g, "xsGetUnitOwner(3)") == 1
    assert value(g, "xsGetUnitOwner(21)") == 2                          # the enemy militia: above the deer (20)
    g.soldiers["a-2"] = "ARCHER"                                       # trained later
    assert value(g, "xsGetUnitOwner(22)") == 1 and g.xs_ids["a-2"] == 22
    assert value(g, "xsGetUnitOwner(21)") == 2                          # an id is never given again


def test_unit_exists_and_number_of_objects():
    g = game()
    assert value(g, "xsDoesUnitExist(7)", "bool") and not value(g, "xsDoesUnitExist(8)", "bool")
    assert value(g, "xsGetPlayerNumberOfObjects(1)") == 3 and value(g, "xsGetPlayerNumberOfObjects(2)") == 1
    del g.soldiers["a-1"]
    assert not value(g, "xsDoesUnitExist(7)", "bool")


def test_hit_points_of_a_unit_and_of_a_building():
    g = game()
    assert value(g, "xsGetUnitHitpoints(7)", "float") == 25.0
    assert value(g, "xsGetUnitHitpoints(3)", "float") == 550.0


def test_position_in_tiles():
    assert value(game(), "xsGetUnitPosition(7)", "vector") == (2.5, 5.5, 0.0)


def test_kind_name_class_copy_and_civilization():
    g = game()
    assert value(g, "xsGetUnitCopyId(9)") == record.types()["VILLAGER_FEMALE"]
    assert value(g, "xsGetUnitName(7, true)", "string") == "ARCHER"
    assert value(g, "xsGetUnitName(9)", "string") == "Villager female"
    assert value(g, "xsGetUnitClass(7)") > 0
    assert value(g, "xsGetUnitCivName(21)", "string") == "Aztecs"
    assert value(g, f"xsIsObjectValid({ARCHER})", "bool") and not value(g, "xsIsObjectValid(-5)", "bool")


def test_the_load_of_a_villager():
    g = game()
    g.villagers["v-1"].load, g.villagers["v-1"].res = 7, "gold"
    assert value(g, "xsGetUnitAttributeHeld(9, 3)", "float") == 7.0
    assert value(g, "xsGetUnitAttributeHeld(9, 1)", "float") == 0.0


def test_an_unknown_unit_gives_one_warning_and_the_script_goes_on(capsys):
    g = game()
    assert value(g, "xsGetUnitOwner(99) + xsGetUnitOwner(99)") == -2
    assert value(g, "xsGetUnitPosition(99)", "vector") == (-1.0, -1.0, -1.0)
    assert capsys.readouterr().err.count("XS script: unknown unit 99: skipped") == 1 + 1   # one per host (each value())
