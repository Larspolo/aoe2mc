"""game/repair.py: selected villagers on the shore repair an own damaged ship, as in AoE2 DE (#1661): the siege rate
(repair.SIEGE of the building rate), for half the training cost, from up to 2 tiles away."""
import pytest
from test_gather import grid
from test_repair_siege import CrewServer

from game import combat, gather, repair, train

GALLEY = combat.stats("GALLEY").hp


class ShipServer(CrewServer):
    """A CrewServer whose crews have the hit points of a galley."""

    def command(self, cmd):
        out = super().command(cmd)
        return out.replace(f"is {combat.stats('BATTERING_RAM').hp}.0", f"is {GALLEY}.0") if "max_health" in cmd else out


def setup(hp=60.0, x=12.5, wood=100, gold=100):
    """A 24 × 24 map (tile size 1): land at x < 11, water from x = 11. An own galley at (x, 12.5) with hp hit points
    and an own villager at (5.5, 12.5)."""
    rows = [[64] * 11 + ["-"] * 13 for _ in range(24)]
    objects = [{"kind": "unit", "name": "GALLEY", "player": 1, "uuid": "ship", "tile": [x, 12.5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [5.5, 12.5]}]
    server = ShipServer({"ship": {"Pos": (x, 63.0, 12.5)}, "v0": {"Pos": (5.5, 64.0, 12.5)}}, {"ship": hp})
    g = gather.Gather(server, grid(rows, objects), start={"wood": wood, "gold": gold}).setup()
    g.choose(set(g.villagers), "v0")
    return server, g


def test_a_villager_on_the_shore_repairs_a_galley_to_its_full_hit_points_for_half_the_cost():
    server, g = setup()
    assert g.soldiers.get("ship") == "GALLEY" and repair.unit_order(g, "Steve", "ship")
    end = g.villagers["v0"].path[-1]                                  # the shore within 2 tiles of the ship
    assert g.map.free(*end) and 12 - end[0] <= repair.REACH
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 20000:
        g.step()
        steps += 1
    assert server.health["ship"] == GALLEY and g.villagers["v0"].state == "idle"
    full = train.price(g, "GALLEY")                                   # 90 wood, 30 gold: half for all hit points
    lost = GALLEY - 60
    assert 100 - g.stock["wood"] == int(full["wood"] / 2 * lost / GALLEY)
    assert 100 - g.stock["gold"] == int(full["gold"] / 2 * lost / GALLEY)


def test_the_ship_rate_is_the_siege_rate():
    server, g = setup()
    repair.unit_order(g, "Steve", "ship")
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)
    assert server.health["ship"] == pytest.approx(60 + repair.RATE * repair.SIEGE * 8)


def test_a_ship_that_sails_away_stops_the_repair():
    server, g = setup()
    repair.unit_order(g, "Steve", "ship")
    g.villagers["v0"].state = "repair"
    repair.tick(g, 1.0)
    assert server.health["ship"] > 60 and g.villagers["v0"].state == "repair"
    server.entities["ship"]["Pos"] = (16.5, 63.0, 12.5)
    before = server.health["ship"]
    repair.tick(g, 1.0)
    assert server.health["ship"] == before and g.villagers["v0"].state == "idle" and not g.repairs


def test_a_ship_far_from_the_shore_or_with_full_hit_points_is_not_a_repair_order():
    g = setup()[1]
    assert repair.shore(g, (12, 12)) == {(10, z) for z in range(10, 15)} and not repair.shore(g, (13, 12))
    server, g = setup(x=20.5)
    assert not repair.unit_order(g, "Steve", "ship") and not vars(g).get("repairs")
    server, g = setup(hp=float(GALLEY))
    assert not repair.unit_order(g, "Steve", "ship")
