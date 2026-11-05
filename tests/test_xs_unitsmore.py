"""More XS unit reads (game/xs_host.py, #5847): unit lists in arrays, the garrison, attributes, targets, build points."""
from game import xs_host
from game.xs_run import Xs
from tests.test_xs_unitsread import ARCHER, game

RECT = (8, 16, 8, 16)                                                  # the house of game(): (x0, x1, z0, z1)


def run(g, body, typ="int"):
    init = {"string": '""', "vector": "vector(0, 0, 0)", "float": "0.0"}.get(typ, "0")
    x = Xs(f"{typ} r = {init}; void main() {{ {body} }}", out=print, host=xs_host.host(g))
    x.tick(0)
    return x.get("r")


def test_the_unit_ids_of_a_player_in_an_array():
    g = game()
    assert run(g, "int a = xsGetPlayerUnitIds(1); r = xsArrayGetSize(a);") == 3
    assert run(g, f"int a = xsGetPlayerUnitIds(1, {ARCHER}); r = xsArrayGetInt(a, 0) * 10 + xsArrayGetSize(a);") == 71
    assert run(g, "int a = xsArrayCreateInt(5, 0); int b = xsGetPlayerUnitIds(2, -1, a); r = (a == b) * 10 "
                  "+ xsArrayGetSize(a);") == 11


def test_the_garrison_of_a_house():
    g = game()
    g.garrisons = {RECT: ["v-1"]}
    assert run(g, "r = xsGetGarrisonedInUnitId(9);") == 3
    assert run(g, "r = xsGetGarrisonedInUnitId(7);") == -1
    assert run(g, "int a = xsGetGarrisonedUnitIds(3); r = xsArrayGetSize(a) * 100 + xsArrayGetInt(a, 0);") == 109


def test_attribute_owner_name_caption_and_type():
    g = game()
    g.data["players"]["1"]["name"] = "Ann"
    assert run(g, "r = xsGetUnitAttribute(7, 12);", "float") > 0
    assert run(g, "r = xsGetUnitPlayerName(7);", "string") == "Ann"
    assert run(g, "r = xsGetUnitCaption(7);", "string") == "Archer"
    assert run(g, "r = xsGetUnitType(3);") == 2 and run(g, "r = xsGetUnitType(7);") == 4


def test_build_points_gather_point_move_and_attack_targets():
    g = game()
    g.sites = [{"name": "HOUSE", "player": 1, "footprint": (40, 48, 40, 48), "progress": 0.25}]
    g.rally = {RECT: ((20, 28), None)}
    assert run(g, "r = xsGetUnitBuildPoints(21);", "float") == 0.25     # the site takes the next id
    assert run(g, "r = xsGetUnitBuildPoints(3);", "float") == 1.0
    assert run(g, "r = xsGetUnitGatherPoint(3);", "vector") == (5.125, 7.125, 0.0)
    g.villagers["v-1"].goal = (8, 12)
    assert run(g, "r = xsGetUnitMoveTarget(9);", "vector") == (2.125, 3.125, 0.0)
    g.villagers["v-1"].prey = "d-1"
    assert run(g, "r = xsGetUnitTargetUnitId(9);") == 20
    g.bots[0].targets = {"e-1": "a-1"}
    assert run(g, "r = xsGetUnitTargetUnitId(22);") == 7 and run(g, "r = xsGetUnitTargetUnitId(7);") == -1
