"""game/repair.py: selected villagers repair an own damaged mule cart (#2504, AoE2 wiki "Mule Cart", "Repairing"). The
mule cart is a building (build.MOVES): the building rate and half its build cost, with the Georgian team bonus. Its
mob is a mule with no crew: the commands run on the mule itself."""
import re

from test_gather import FakeServer, grid

from game import build, gather, repair

FULL = 300.0                                                       # buildings.jsonl MULE_CART


class MuleServer(FakeServer):
    """A FakeServer that keeps the Health of each mule (the hit points of a mule cart)."""

    def __init__(self, entities, health):
        super().__init__(entities)
        self.health = health

    def command(self, cmd):
        if m := re.fullmatch(r"execute as (\S+) run data get entity @s Health", cmd):
            self.log.append(cmd)
            return f"Mule has the following entity data: {self.health[m[1]]}f" if m[1] in self.health else ""
        if m := re.fullmatch(r"execute as (\S+) run attribute @s minecraft:max_health get", cmd):
            self.log.append(cmd)
            return f"Base value of attribute Max Health for entity Mule is {FULL}" if m[1] in self.health else ""
        if m := re.fullmatch(r"execute as (\S+) run data modify entity @s Health set value ([\d.]+)f", cmd):
            self.health[m[1]] = float(m[2])
        return super().command(cmd)


def setup(hp, civ="ARMENIANS", food=100, wood=100):
    """A flat 24 × 24 map (tile size 1) with an own mule cart "cart" at hp hit points and one own villager."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [7.5, 4.5]}]
    server = MuleServer({"cart": {"Pos": (12.5, 64.0, 12.5)}, "v0": {"Pos": (7.5, 64.0, 4.5)}}, {"cart": hp})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={"food": food, "wood": wood}).setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["cart"] = "MULE_CART"                                   # build.cart summons it (train.summon)
    g.choose(set(g.villagers), "v0")
    return server, g


def repair_all(g):
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 5000:
        g.step()
        steps += 1


def test_a_villager_repairs_a_damaged_mule_cart_at_the_building_rate():
    server, g = setup(hp=100.0)
    assert g.soldiers.get("cart") in build.MOVES and repair.unit_order(g, "Steve", "cart")
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)
    assert server.health["cart"] == 100 + 750 / 60 * 8                 # not the siege rate (25 %)


def test_the_full_repair_takes_the_repair_cost():
    for civ in ("ARMENIANS", "GEORGIANS"):
        server, g = setup(hp=1.0, civ=civ)
        cost = repair.cost(g, "MULE_CART")
        assert repair.unit_order(g, "Steve", "cart")
        repair_all(g)
        assert server.health["cart"] == FULL and g.villagers["v0"].state == "idle", civ
        share = (FULL - 1) / FULL
        assert (100 - g.stock["food"], 100 - g.stock["wood"]) == \
            (int(cost.get("food", 0) * share), int(cost.get("wood", 0) * share)), civ


def test_a_click_on_a_mule_cart_with_its_full_hit_points_is_no_repair_order():
    server, g = setup(hp=FULL)
    assert not repair.unit_order(g, "Steve", "cart")
