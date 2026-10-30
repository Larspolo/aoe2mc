"""game/repair.py: selected villagers repair an own damaged building, as in AoE2 DE (#1330): the first one at
repair.RATE, each other one repair.MORE more, for half the build cost (a town center: double its wood)."""
import re

import pytest
from test_gather import FakeServer, grid

from game import build, combat, garrison, gather, repair

HOUSE, TC = (4, 6, 4, 6), (12, 16, 12, 16)                         # block footprints (x0, x1, z0, z1)


class HpServer(FakeServer):
    """A FakeServer that keeps the scores aoe_hp of the building targets."""

    def __init__(self, entities, hp):
        super().__init__(entities)
        self.hp = hp

    def command(self, cmd):
        if m := re.fullmatch(r"scoreboard players get (\S+) aoe_hp", cmd):
            self.log.append(cmd)
            return f"{m[1]} has {self.hp[m[1]]} [aoe_hp]" if m[1] in self.hp else f"Can't get value of aoe_hp for {m[1]}"
        if m := re.fullmatch(r"scoreboard players set (\S+) aoe_hp (\d+)", cmd):
            self.hp[m[1]] = int(m[2])
        return super().command(cmd)


def setup(house=275, tc=2400, wood=100, n=1):
    """A flat 24 × 24 map (tile size 1) with an own house and town center at the hit points house and tc, and n own
    villagers "v0" ... next to the house."""
    objects = [{"kind": "building", "name": "HOUSE", "player": 1, "tile": [5, 5], "footprint": [4, 4, 6, 6]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [14, 14], "footprint": [12, 12, 16, 16]}]
    ents = {}
    for k in range(n):
        objects.append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [7.5, 4.5 + k]})
        ents[f"v{k}"] = {"Pos": (7.5, 64.0, 4.5 + k)}
    server = HpServer(ents, {repair.uuid(HOUSE): house, repair.uuid(TC): tc})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={"wood": wood}).setup()
    g.choose(set(g.villagers), "v0")
    return server, g


def test_the_repair_costs_half_the_build_cost():
    _, g = setup()
    for name in ("HOUSE", "CASTLE"):
        assert repair.cost(g, name) == {r: v / 2 for r, v in build.price(g, name).items()}
    assert repair.cost(g, "TOWN_CENTER") == {"wood": build.price(g, "TOWN_CENTER")["wood"] * 2}   # no stone (AoE2 wiki)


def test_a_villager_repairs_a_damaged_house_to_its_full_hit_points_and_pays_half_the_cost():
    server, g = setup()
    assert repair.order(g, "Steve", (4, 5)) == HOUSE
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 1000:
        g.step()
        steps += 1
    full = combat.stats("HOUSE").hp
    assert server.hp[repair.uuid(HOUSE)] == full
    assert abs(100 - g.stock["wood"] - repair.cost(g, "HOUSE")["wood"] * (full - 275) / full) <= 1   # whole wood
    assert f"aoe label {repair.uuid(HOUSE)}" in server.log


def test_the_rate_of_one_and_of_two_villagers():
    server, g = setup(house=100, n=2)
    repair.order(g, "Steve", (4, 5))
    for v in g.villagers.values():
        v.state = "repair"
    repair.tick(g, 8.0)                                              # 8 AoE2 s: 100 + 50 hit points per villager
    assert server.hp[repair.uuid(HOUSE)] == 100 + round((repair.RATE + repair.MORE) * 8)
    g.villagers["v1"].state = "idle"                                 # another order
    repair.tick(g, 8.0)
    assert server.hp[repair.uuid(HOUSE)] == 250 + round(repair.RATE * 8)


def test_the_repair_stops_with_a_chat_line_when_the_stock_is_empty():
    server, g = setup(tc=1200, wood=0)
    assert repair.order(g, "Steve", (13, 13)) == TC
    g.villagers["v0"].state = "repair"
    repair.tick(g, 1.0)
    assert server.hp[repair.uuid(TC)] == 1200 and g.villagers["v0"].state == "idle"
    assert any(c.startswith("tellraw") and "Not enough resources to repair the town center" in c for c in server.log)


def test_a_click_on_an_undamaged_building_still_garrisons_the_selection():
    server, g = setup(tc=2400)
    assert repair.order(g, "Steve", (13, 13)) is None
    g.paper = True
    assert garrison.order(g, "Steve", (13, 13)) == TC and g.entering == {"v0": TC}


@pytest.mark.parametrize("cell", [(20, 20), None])
def test_no_repair_order_off_an_own_building(cell):
    _, g = setup()
    assert repair.order(g, "Steve", cell) is None and g.villagers["v0"].state == "idle"


@pytest.mark.mc
def test_repair_on_a_server(tmp_path):
    """2 villagers walk to their damaged town center (400 hit points less than the full hit points) and repair it on a
    Paper server: the score aoe_hp of its target entity goes up to the full hit points, and the stock pays the share
    of the repair cost."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=6, y=6)
    for k in range(2):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=4.5 + 2 * k, y=13.5)
    src = str(tmp_path / "r.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={"wood": 200}).setup()
        tc, = repair.buildings(g)
        full = combat.stats("TOWN_CENTER").hp
        game.command(f"scoreboard players set {repair.uuid(tc)} aoe_hp {full - 400}")
        assert repair.hp(g, tc) == full - 400
        g.choose(set(g.villagers), min(g.villagers))
        assert repair.order(g, "nobody", (tc[0], tc[2])) == tc
        end = time.time() + 90
        while repair.hp(g, tc) < full:
            assert time.time() < end, ({u: (v.state, g.pos(u)) for u, v in g.villagers.items()}, repair.hp(g, tc))
            g.step()
            time.sleep(g.tick)
        assert abs(200 - g.stock["wood"] - repair.cost(g, "TOWN_CENTER")["wood"] * 400 / full) <= 1
        assert all(v.state == "idle" for v in g.villagers.values())
