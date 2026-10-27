"""game/train.py: the siege upgrades of AoE2 DE (#1352). The siege workshop researches Capped Ram, Siege Ram, Onager,
Siege Onager and Heavy Scorpion in the Imperial Age, and each one turns the live units of its line into the next unit.
The university researches Siege Engineers: +1 range for the ranged siege units, +20 % attack against buildings."""
import contextlib
import io
import json

import pytest
from test_forging import menus
from test_gather import FakeServer, grid

from game import combat, gather, run, train

WORKSHOP, UNIVERSITY = (11, 3), (17, 3)                           # a block cell in each building
UPGRADES = {"CAPPED_RAM_UPGRADE": ({"food": 300}, 50), "SIEGE_RAM_UPGRADE": ({"food": 1000}, 75),   # AoE2 DE wiki:
            "ONAGER_UPGRADE": ({"food": 800, "gold": 500}, 75),                                     # UpCost, UpTime
            "SIEGE_ONAGER_UPGRADE": ({"food": 1450, "gold": 1000}, 150),
            "HEAVY_SCORPION_UPGRADE": ({"food": 800, "wood": 750}, 50)}


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


@pytest.mark.parametrize("name", sorted(UPGRADES) + ["SIEGE_ENGINEERS"])
def test_each_upgrade_has_the_wiki_cost_time_and_the_imperial_age(name):
    cost, time = UPGRADES.get(name, ({"food": 500, "wood": 600}, 45))
    assert train.COSTS[name] == cost and train.TRAIN_TIMES[name] == time


def test_no_upgrade_before_the_imperial_age():
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", WORKSHOP)
    assert ":book:" not in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "ONAGER_UPGRADE") is None


def test_the_second_upgrade_of_a_line_only_after_the_first():
    server, g = setup()
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 3:book:Capped Ram:300 food · 50 s · research " in menu and "Siege Ram" not in menu
    assert " 4:book:Onager:800 food · 500 gold · 75 s · research " in menu and "Siege Onager" not in menu
    assert " 5:book:Heavy Scorpion:800 food · 750 wood · 50 s · research " in menu
    assert train.queue(g, "Steve", WORKSHOP, "SIEGE_ONAGER_UPGRADE") is None
    research(g, WORKSHOP, "ONAGER_UPGRADE")
    rect = train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 4:book:Siege Onager:1450 food · 1000 gold · 150 s · research " in menu and ":book:Onager:" not in menu
    assert " 1:dispenser:Onager:" in menu                                     # the workshop trains onagers
    food = g.stock["food"]
    assert train.order(g, "Steve", rect, 4) == 1 and g.stock["food"] == food - 1450   # the click takes the shown one


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


def test_siege_engineers_adds_range_and_attack_against_buildings():
    server, g = setup()
    train.open_menu(g, "Steve", UNIVERSITY)
    assert " 1:book:Siege Engineers:500 food · 600 wood · 45 s · research " in menus(server)[-1] + " "
    research(g, UNIVERSITY, "SIEGE_ENGINEERS")
    m, r, s = (train.stats(g, n) for n in ("MANGONEL", "BATTERING_RAM", "SCORPION"))
    assert (m.range, m.bonus["building"]) == (8, 42)                           # 7 + 1, 35 × 1.2
    assert (r.range, r.bonus["building"]) == (0, 180)                          # a ram: no range, 150 × 1.2
    assert (s.range, s.bonus["building"]) == (8, 4)                            # 3 × 1.2 (#1402)
    assert train.stats(g, "ARCHER") == combat.stats("ARCHER")                  # not a siege unit
    assert "aoe range m 8 71 1.0 3" in server.log                              # range 8 blocks (T 1), blast, min range
    assert "aoe stats r 175 2 -3 180 0 siege,ram building:180,siege:40 59" in server.log   # 180 more vs. buildings


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
        g.stock.update(food=800, gold=500)
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "ONAGER_UPGRADE")
        train.tick(g, train.TRAIN_TIMES["ONAGER_UPGRADE"])
        assert g.soldiers[uuid] == "ONAGER"
        assert game.command(combat.range_command(uuid, "ONAGER", g.map.T)).strip() == "Range: 1 units"
        name = game.command(f"data get entity {uuid} Passengers[0].CustomName")    # the crew has the name line
        assert "Onager" in name and "Mangonel" not in name and "color" in name, name   # the player color stays
