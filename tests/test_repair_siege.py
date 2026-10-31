"""game/repair.py: selected villagers repair an own damaged siege unit, as in AoE2 DE (#1331): a share of the building
rate (repair.SIEGE), for half the training cost."""
import re

import pytest
from test_gather import FakeServer, grid
from test_lang_orders import plain_log

from game import combat, gather, repair, train

RAM = combat.stats("BATTERING_RAM").hp


class CrewServer(FakeServer):
    """A FakeServer that keeps the Health of the crew of each minecart (the hit points of a siege unit)."""

    def __init__(self, entities, health):
        super().__init__(entities)
        self.health = health

    def command(self, cmd):
        if m := re.fullmatch(r"execute as (\S+) on passengers run data get entity @s Health", cmd):
            self.log.append(cmd)
            return f"Crew has the following entity data: {self.health[m[1]]}f" if m[1] in self.health else ""
        if m := re.fullmatch(r"execute as (\S+) on passengers run attribute @s minecraft:max_health get", cmd):
            self.log.append(cmd)
            return f"Base value of attribute Max Health for entity Crew is {RAM}.0" if m[1] in self.health else ""
        if m := re.fullmatch(r"execute as (\S+) on passengers run data modify entity @s Health set value ([\d.]+)f", cmd):
            self.health[m[1]] = float(m[2])
        return super().command(cmd)


def setup(hp=100.0, wood=100, gold=100, n=1):
    """A flat 24 × 24 map (tile size 1) with an own battering ram "ram" at hp hit points and n own villagers."""
    objects = [{"kind": "unit", "name": "BATTERING_RAM", "player": 1, "uuid": "ram", "tile": [12.5, 12.5]}]
    ents = {"ram": {"Pos": (12.5, 64.0, 12.5)}}
    for k in range(n):
        objects.append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [7.5, 4.5 + k]})
        ents[f"v{k}"] = {"Pos": (7.5, 64.0, 4.5 + k)}
    server = CrewServer(ents, {"ram": hp})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={"wood": wood, "gold": gold}).setup()
    g.choose(set(g.villagers), "v0")
    return server, g


def test_a_villager_repairs_a_damaged_ram_to_its_full_hit_points_and_pays_half_the_cost():
    server, g = setup(hp=RAM - 35)
    assert "ram" in g.soldiers and repair.unit_order(g, "Steve", "ram")
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 5000:
        g.step()
        steps += 1
    assert server.health["ram"] == RAM and g.villagers["v0"].state == "idle"
    full = train.price(g, "BATTERING_RAM")                            # half for all hit points
    assert 100 - g.stock["wood"] == int(full["wood"] / 2 * 35 / RAM) and 100 - g.stock["gold"] == int(full["gold"] / 2 * 35 / RAM)


def test_the_siege_rate_of_one_and_of_two_villagers():
    server, g = setup(hp=50.0, n=2)
    repair.unit_order(g, "Steve", "ram")
    for v in g.villagers.values():
        v.state = "repair"
    repair.tick(g, 8.0)
    assert server.health["ram"] == pytest.approx(50 + (repair.RATE + repair.MORE) * repair.SIEGE * 8)


def test_a_ram_that_moves_stops_the_repair():
    server, g = setup(hp=50.0)
    repair.unit_order(g, "Steve", "ram")
    g.villagers["v0"].state = "repair"
    repair.tick(g, 1.0)
    assert server.health["ram"] > 50 and g.villagers["v0"].state == "repair"
    server.entities["ram"]["Pos"] = (14.5, 64.0, 12.5)
    before = server.health["ram"]
    repair.tick(g, 1.0)
    assert server.health["ram"] == before and g.villagers["v0"].state == "idle" and not g.repairs


def test_no_repair_of_a_full_ram_or_without_villagers_and_a_click_on_it():
    server, g = setup(hp=float(RAM))
    assert not repair.unit_order(g, "Steve", "ram")
    server, g = setup(hp=50.0)
    g.selected = set()
    assert not repair.unit_order(g, "Steve", "ram") and not repair.unit_order(g, "Steve", "v0")
    server, g = setup(hp=50.0, wood=0)
    repair.unit_order(g, "Steve", "ram")
    g.villagers["v0"].state = "repair"
    repair.tick(g, 60.0)
    assert server.health["ram"] == 50 and g.villagers["v0"].state == "idle"
    assert any("Not enough resources to repair the battering ram" in c for c in plain_log(server.log))


@pytest.mark.mc
def test_siege_repair_on_a_server(tmp_path):
    """A villager walks to its damaged battering ram (75 hit points less than the full hit points: the Health of its
    crew) and repairs it on a Paper server, and pays half the training cost × 75 / the full hit points."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.BATTERING_RAM.ID, x=12.5, y=12.5)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=12.5)
    src = str(tmp_path / "r.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={"wood": 100, "gold": 100}).setup()
        ram, = [u for u, n in g.soldiers.items() if n == "BATTERING_RAM"]
        assert repair.unit_hp(g, ram) == (RAM, RAM)
        game.command(repair.crew(ram) + f"data modify entity @s Health set value {float(RAM - 75)}f")
        g.choose(set(g.villagers), min(g.villagers))
        assert repair.unit_order(g, "nobody", ram)
        end = time.time() + 120
        while repair.unit_hp(g, ram)[0] < RAM:
            assert time.time() < end, ({u: (v.state, g.pos(u)) for u, v in g.villagers.items()}, repair.unit_hp(g, ram))
            g.step()
            time.sleep(g.tick)
        full = train.price(g, "BATTERING_RAM")
        assert (100 - g.stock["wood"], 100 - g.stock["gold"]) == (int(full["wood"] / 2 * 75 / RAM), int(full["gold"] / 2 * 75 / RAM))
        assert all(v.state == "idle" for v in g.villagers.values())
