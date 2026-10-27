"""game/repair.py: selected Serjeants repair an own damaged Donjon, as in AoE2 DE (#2128, AoE2 wiki "Serjeant (Age of
Empires II)": "Can build and repair Donjons"). They repair at the villager rate: the wiki gives no own rate."""
from test_gather import grid
from test_repair import HOUSE, HpServer

from game import gather, repair

DONJON = (10, 12, 4, 6)                                              # block footprint (x0, x1, z0, z1)


def setup(donjon=100, house=100):
    """A flat 24 × 24 map (tile size 1) of a Sicilian player: a damaged house and Donjon, a villager "v0" next to the
    house and a Serjeant "s0" next to the Donjon."""
    objects = [{"kind": "building", "name": "HOUSE", "player": 1, "tile": [5, 5], "footprint": [4, 4, 6, 6]},
               {"kind": "building", "name": "DONJON", "player": 1, "tile": [11, 5], "footprint": [10, 4, 12, 6]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [7.5, 4.5]},
               {"kind": "unit", "name": "SERJEANT", "player": 1, "uuid": "s0", "tile": [12.5, 4.5]}]
    ents = {"v0": {"Pos": (7.5, 64.0, 4.5)}, "s0": {"Pos": (12.5, 64.0, 4.5)}}
    server = HpServer(ents, {repair.uuid(HOUSE): house, repair.uuid(DONJON): donjon})
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"] = {"1": {"civ": "SICILIANS"}}
    g = gather.Gather(server, data, start={"wood": 100, "stone": 100}).setup()
    return server, g


def test_a_serjeant_repairs_an_own_damaged_donjon_at_the_villager_rate_and_the_stock_pays():
    server, g = setup()
    assert g.soldiers["s0"] == "SERJEANT"
    g.choose({"s0"}, "s0")
    assert repair.order(g, "Steve", (10, 5)) == DONJON
    assert any(c.startswith("aoe moveto s0 ") for c in server.log)   # it walks with the plugin path finding
    repair.tick(g, 8.0)
    gain = server.hp[repair.uuid(DONJON)] - 100
    assert gain == round(repair.RATE * 8)
    assert g.stock["stone"] < 100 and g.stock["wood"] <= 100         # half of 50 wood and 175 stone for the full HP


def test_a_serjeant_does_not_repair_a_house():
    server, g = setup()
    g.choose({"s0"}, "s0")
    assert repair.order(g, "Steve", (4, 5)) is None
    repair.tick(g, 8.0)
    assert server.hp[repair.uuid(HOUSE)] == 100


def test_a_serjeant_and_a_villager_repair_the_donjon_together():
    server, g = setup()
    g.choose({"s0", "v0"}, "s0")
    assert repair.order(g, "Steve", (10, 5)) == DONJON
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)
    assert server.hp[repair.uuid(DONJON)] == 100 + round((repair.RATE + repair.MORE) * 8)


def test_a_move_order_ends_the_repair_of_a_serjeant():
    server, g = setup()
    g.choose({"s0"}, "s0")
    repair.order(g, "Steve", (10, 5))
    g.walk_to("Steve", (20, 20))
    repair.tick(g, 8.0)
    assert server.hp[repair.uuid(DONJON)] == 100
