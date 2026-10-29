"""game/train.py: the siege upgrades of AoE2 DE (#1352). The siege workshop researches Capped Ram, Siege Ram, Onager,
Siege Onager and Heavy Scorpion in the Imperial Age, and each one turns the live units of its line into the next unit."""
import contextlib
import io
import json

import pytest
from test_forging import menus
from test_gather import FakeServer, grid

from game import combat, gather, run, train

WORKSHOP = (11, 3)                                                # a block cell in the siege workshop


def setup(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")):
    """A flat 24 × 24 map (tile size 1): a built siege workshop at x 10-12, z 2-4 and a university at x 16-18, z 2-4
    of player 1, a ram "r", a mangonel "m" and a scorpion "s", and many resources."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x, 9.5]}
               for u, n, x in (("r", "BATTERING_RAM", 5.5), ("m", "MANGONEL", 9.5), ("s", "SCORPION", 13.5))]
    server = FakeServer({u: {"Pos": (x, 64.0, 9.5)} for u, x in (("r", 5.5), ("m", 9.5), ("s", 13.5))})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.sites += [{"name": "SIEGE_WORKSHOP", "player": 1, "footprint": [10, 13, 2, 5], "done": True},
                {"name": "UNIVERSITY", "player": 1, "footprint": [16, 19, 2, 5], "done": True}]
    g.stock.update(food=10000, wood=10000, gold=10000)
    g.techs.update(ages)
    return server, g


def research(g, cell, name):
    assert train.queue(g, "Steve", cell, name), name
    train.tick(g, train.TRAIN_TIMES[name])
    assert name in g.techs


def shown(menu, name):
    """The menu text has the item of name in its slot of the siege workshop."""
    slot, item, label = train.slots("SIEGE_WORKSHOP", name)
    return f" {slot}:{item}:{label}:" in menu


def test_no_upgrade_before_the_imperial_age():
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", WORKSHOP)
    assert ":book:" not in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "ONAGER_UPGRADE") is None


def test_the_second_upgrade_of_a_line_only_after_the_first():
    server, g = setup()
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert shown(menu, "CAPPED_RAM_UPGRADE") and not shown(menu, "SIEGE_RAM_UPGRADE")
    assert shown(menu, "ONAGER_UPGRADE") and not shown(menu, "SIEGE_ONAGER_UPGRADE")
    assert shown(menu, "HEAVY_SCORPION_UPGRADE")
    assert train.queue(g, "Steve", WORKSHOP, "SIEGE_ONAGER_UPGRADE") is None
    research(g, WORKSHOP, "ONAGER_UPGRADE")
    rect = train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert shown(menu, "SIEGE_ONAGER_UPGRADE") and not shown(menu, "ONAGER_UPGRADE")
    assert shown(menu, "ONAGER")                                              # the workshop trains onagers
    food = g.stock["food"]
    slot = train.slots("SIEGE_WORKSHOP", "SIEGE_ONAGER_UPGRADE")[0]
    assert train.order(g, "Steve", rect, slot) == 1                          # the click takes the shown one
    assert g.stock["food"] == food - train.COSTS["SIEGE_ONAGER_UPGRADE"].get("food", 0)


def test_a_live_ram_mangonel_and_scorpion_get_the_values_of_the_next_unit():
    server, g = setup()
    for name in ("CAPPED_RAM_UPGRADE", "ONAGER_UPGRADE", "HEAVY_SCORPION_UPGRADE"):
        research(g, WORKSHOP, name)
    assert (g.soldiers["r"], g.soldiers["m"], g.soldiers["s"]) == ("CAPPED_RAM", "ONAGER", "HEAVY_SCORPION")
    for u, n in (("r", "CAPPED_RAM"), ("m", "ONAGER"), ("s", "HEAVY_SCORPION")):
        assert combat.stats_command(u, n, train.stats(g, n)) in server.log and f"aoe label {u} {n.replace('_', ' ').title()}" in server.log
    assert combat.range_command("m", "ONAGER", 1) in server.log                # range 8 and the onager blast
    research(g, WORKSHOP, "SIEGE_RAM_UPGRADE")
    research(g, WORKSHOP, "SIEGE_ONAGER_UPGRADE")
    assert (g.soldiers["r"], g.soldiers["m"]) == ("SIEGE_RAM", "SIEGE_ONAGER")
    assert train.trains(g, "SIEGE_WORKSHOP")[:3] == ("SIEGE_RAM", "SIEGE_ONAGER", "HEAVY_SCORPION")


@pytest.mark.mc
def test_the_onager_upgrade_on_a_server(tmp_path):
    """A live mangonel becomes an onager on a Paper server: the hit points of its crew and its name."""
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.SIEGE_WORKSHOP.ID, x=4.5, y=4.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MANGONEL.ID, x=10.5, y=10.5)
    src = str(tmp_path / "siege.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        uuid, = [u for u, n in g.soldiers.items() if n == "MANGONEL"]
        g.techs.update({"FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"})
        g.stock.update(train.COSTS["ONAGER_UPGRADE"])
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "ONAGER_UPGRADE")
        train.tick(g, train.TRAIN_TIMES["ONAGER_UPGRADE"])
        assert g.soldiers[uuid] == "ONAGER"
        assert game.command(combat.range_command(uuid, "ONAGER", g.map.T)).strip() == "Range: 1 units"
        name = game.command(f"data get entity {uuid} Passengers[0].CustomName")    # the crew has the name line
        assert "Onager" in name and "Mangonel" not in name and "color" in name, name   # the player color stays
