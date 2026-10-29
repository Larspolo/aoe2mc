"""game/train.py: an own siege workshop trains the Battering Ram, the Mangonel and the Scorpion with their cost and time
of the data, from their age (#1349)."""
import re

import pytest
from test_gather import FakeServer, grid
from test_loom import menus

import units
from game import combat, gather, train

build = train.build                                                    # the module that train uses
SHOP = (2, 6, 2, 6)                                                    # block footprint (x0, x1, z0, z1)
NAMES = ("BATTERING_RAM", "MANGONEL", "SCORPION", "SIEGE_TOWER")


def setup(ages=2):
    objects = [{"kind": "building", "name": "SIEGE_WORKSHOP", "player": 1, "tile": [4.0, 4.0], "footprint": [2, 2, 6, 6]},
               {"kind": "building", "name": "HOUSE", "player": 1, "tile": [11.0, 11.0], "footprint": [10, 10, 12, 12]}]
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.techs |= set(build.AGE_TECHS[:ages])
    g.stock.update(wood=1000, gold=1000)
    return server, g


@pytest.mark.parametrize("ages", [0, 1])
def test_the_siege_units_are_locked_before_their_age(ages):
    server, g = setup(ages)
    assert train.open_menu(g, "Steve", (3, 3)) == SHOP
    names = [n for n in NAMES if build.AGE[n] > ages]
    assert all(build.locked(g, n) for n in names)
    text = menus(server)[-1]                                           # the names, not a count: regional units (#2139)
    assert all(re.search(f":{train.ITEMS[n][2]}:[^:]*{build.locked(g, n)}", text) for n in names)
    assert build.AGE["MANGONEL"] <= ages or not train.queue(g, "Steve", (3, 3), "MANGONEL")
    assert g.stock["wood"] == 1000


def test_a_trained_ram_is_a_siege_unit_with_the_aoe2_values():
    server, g = setup()
    cost = train.COSTS["BATTERING_RAM"]
    assert train.order(g, "Steve", SHOP, train.slots("SIEGE_WORKSHOP", "BATTERING_RAM")[0]) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (1000 - cost.get("wood", 0), 1000 - cost.get("gold", 0))
    assert train.tick(g, train.TRAIN_TIMES["BATTERING_RAM"] - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert units.siege("BATTERING_RAM") and re.match(r"summon minecraft:minecart ", summon)
    assert combat.stats_command(uuid, "BATTERING_RAM") in server.log and f"aoe speed {uuid} " in " ".join(server.log)
    assert g.soldiers[uuid] == "BATTERING_RAM" and uuid not in g.villagers


@pytest.mark.mc
def test_a_trained_ram_has_its_values_and_drives_to_an_order_on_a_server(tmp_path):
    """train.summon (the end of a training) makes a minecart with its crew; its first order makes the carrier (#836)."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import math
    import time

    import aoe2mc
    import scenarios

    from game import ai, run
    src = str(tmp_path / "t.aoe2scenario")
    scenarios.save(scenarios.new_scenario(24), src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25).setup()
        x, z = 40, 40
        ram = train.summon(g, "BATTERING_RAM", (x + 0.5, float(g.map.y(x, z)), z + 0.5))
        # one attribute: the server cuts the text of a long NBT answer ("..."), and the order of the list varies (#1713)
        crew = game.command(f'data get entity {ram} Passengers[0].attributes[{{id:"minecraft:max_health"}}].base')
        hp = float(combat.stats("BATTERING_RAM").hp)
        assert ram and crew.rstrip().endswith(f" {hp}d"), crew         # aoe stats: the AoE2 hit points of the ram
        assert ai.move(g, ram, "BATTERING_RAM", g.map.T, x + 12.5, g.map.y(x + 12, z), z + 0.5).strip() == "Moved 1 units"
        end, pos = time.time() + 30, None
        while time.time() < end and not (pos and math.dist((pos[0], pos[2]), (x + 12.5, z + 0.5)) < 2):
            time.sleep(1)
            pos = g.positions([ram]).get(ram)
        assert pos and math.dist((pos[0], pos[2]), (x + 12.5, z + 0.5)) < 2, pos
