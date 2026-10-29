"""game/train.py: a castle trains the unique unit of the civilization of its player (#708): its menu shows the unit
with its AoE2 cost and time, a click queues it, and the new unit has the look of the converter and the AoE2 values."""
import contextlib
import io
import json
import re
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid
from test_train_menu import entry

from game import build, combat, gather, run, train


def setup(civ="BRITONS", food=0, wood=35, gold=40, ages=2):
    """A flat 24 × 24 map (tile size 1): a castle of player 1 at blocks x 10-13, z 2-5 and a town center for the
    population. Steve stands south of the castle. The player has researched ages ages (2: the Castle Age, #1082)."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [12.0, 4.0], "footprint": [10, 2, 14, 6]}]
    data = grid([[64] * 24 for _ in range(24)], objects) | {"players": {"1": {"civ": civ, "color": "blue"}}}
    server = FakeServer({"Steve": {"Pos": (12.0, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, data, start={}).setup()
    g.stock.update(food=food, wood=wood, gold=gold)
    g.techs.update(build.AGE_TECHS[:ages])
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def unique(civ):
    """The unique unit of civ and the setup() stock of its cost."""
    name = train.UNIQUE[civ]
    return name, {r: train.COSTS[name].get(r, 0) for r in ("food", "wood", "gold")}


def test_the_castle_menu_has_the_unique_unit_of_the_civilization():
    for civ in ("BRITONS", "PERSIANS"):
        name, cost = unique(civ)
        server, g = setup(civ, **cost)
        rect = train.open_menu(g, "Steve", (12, 4))
        assert rect == (10, 14, 2, 6) and len(menus(server)) == 1
        assert f" {entry(g, rect, name)}queue 0/15" in menus(server)[0], civ


def test_a_unique_unit_without_combat_values_is_not_in_the_menu(monkeypatch):
    assert all(u in combat.STATS for u in train.UNIQUE.values() if u in train.COSTS)
    monkeypatch.delitem(train.COSTS, "JAGUAR_WARRIOR")                 # the rule needs one unit that the data does not list
    server, g = setup("AZTECS")
    assert train.trains(g, "CASTLE") == train.TRAINS["CASTLE"] + ("ATLATL", "GARLAND_WARS") and train.queue(g, "Steve", (12, 4), "LONGBOWMAN") is None


def test_a_click_queues_the_unit_and_takes_its_cost():
    name, cost = unique("BRITONS")
    server, g = setup(**cost)
    rect = train.open_menu(g, "Steve", (12, 4))
    slot = train.layout(g, rect)[name][0]
    assert train.order(g, "Steve", rect, slot) == 1 and g.queues[rect][0]["name"] == name
    assert g.stock["food"] == g.stock["wood"] == g.stock["gold"] == 0
    assert train.order(g, "Steve", rect, slot) == 0                  # no resources for a second one


def test_the_longbowman_appears_with_the_converter_look_and_the_aoe2_values():
    server, g = setup(**unique("BRITONS")[1])
    rect = train.open_menu(g, "Steve", (12, 4))
    train.order(g, "Steve", rect, train.layout(g, rect)["LONGBOWMAN"][0])
    assert train.tick(g, train.TRAIN_TIMES["LONGBOWMAN"] - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:skeleton \S+ 64.0 6.5 ", summon)
    assert g.soldiers == {uuid: "LONGBOWMAN"}
    s = train.stats(g, "LONGBOWMAN")                                  # Britons in the Castle Age: more range (#1090)
    assert s.range > combat.stats("LONGBOWMAN").range and combat.stats_command(uuid, "LONGBOWMAN", s) in server.log
    assert combat.range_command(uuid, "LONGBOWMAN", 1, s=s) in server.log  # it shoots from its AoE2 range


def test_the_war_elephant_is_a_ravager_with_its_rider():
    server, g = setup("PERSIANS", **unique("PERSIANS")[1])
    rect = train.open_menu(g, "Steve", (12, 4))
    train.order(g, "Steve", rect, train.layout(g, rect)["WAR_ELEPHANT"][0])
    uuid, = train.tick(g, train.TRAIN_TIMES["WAR_ELEPHANT"])
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:ravager ") and "Passengers" in summon
    assert combat.stats_command(uuid, "WAR_ELEPHANT", combat.stats("WAR_ELEPHANT")) in server.log


@pytest.mark.mc
def test_a_trained_war_elephant_and_longbowman_exist_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.CASTLE.ID, x=5, y=5)   # population 20
    src = str(tmp_path / "castle.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        for civ, name in [("PERSIANS", "WAR_ELEPHANT"), ("BRITONS", "LONGBOWMAN")]:
            data["players"]["1"]["civ"] = civ
            g = gather.Gather(game, data, tick=0.25, start={}).setup()
            g.techs.update(train.build.AGE_TECHS[:2])                    # the Castle Age (#1082)
            g.stock.update(unique(civ)[1])
            rect, = [r for r, b in train.homes(g).items() if b == "CASTLE"]
            assert train.queue(g, "nobody", rect[::2], name)
            uuid, = train.tick(g, train.TRAIN_TIMES[name])
            assert g.pos(uuid) and g.soldiers == {uuid: name}, f"the trained {name} exists"
