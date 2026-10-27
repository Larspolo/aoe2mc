"""game/train.py: a castle trains the unique unit of the civilization of its player (#708): its menu shows the unit
with its AoE2 cost and time, a click queues it, and the new unit has the look of the converter and the AoE2 values."""
import contextlib
import io
import json
import re
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid

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


def test_the_castle_menu_has_the_unique_unit_of_the_civilization():
    server, g = setup()
    assert train.open_menu(g, "Steve", (12, 4)) == (10, 14, 2, 6)
    assert [m.split(" 1:")[0] for m in menus(server)] == [                # item 1: the trebuchet (#1351)
        "aoe menu Steve Castle 0:skeleton_spawn_egg:Longbowman:35 wood · 40 gold · 18 s · queue 0/15"]
    server, g = setup("PERSIANS")
    train.open_menu(g, "Steve", (12, 4))
    assert menus(server)[-1].startswith("aoe menu Steve Castle 0:ravager_spawn_egg:War Elephant:170 food · 85 gold")


def test_a_unique_unit_without_combat_values_is_not_in_the_menu(monkeypatch):
    assert all(u in combat.STATS for u in train.UNIQUE.values() if u in train.COSTS)
    monkeypatch.delitem(train.COSTS, "JAGUAR_WARRIOR")                 # the rule needs one unit that the data does not list
    server, g = setup("AZTECS")
    assert train.trains(g, "CASTLE") == train.TRAINS["CASTLE"] and train.queue(g, "Steve", (12, 4), "LONGBOWMAN") is None


def test_a_click_queues_the_unit_and_takes_its_cost():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (12, 4))
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "LONGBOWMAN"
    assert g.stock["wood"] == 0 and g.stock["gold"] == 0
    assert train.order(g, "Steve", rect, 0) == 0                     # no wood and gold for a second one


def test_the_longbowman_appears_with_the_converter_look_and_the_aoe2_values():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (12, 4))
    train.order(g, "Steve", rect, 0)
    assert train.tick(g, 17) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:skeleton \S+ 64.0 6.5 ", summon)
    assert g.soldiers == {uuid: "LONGBOWMAN"}
    s = train.stats(g, "LONGBOWMAN")                                  # Britons in the Castle Age: +1 range (#1090)
    assert s.range == combat.stats("LONGBOWMAN").range + 1 and combat.stats_command(uuid, "LONGBOWMAN", s) in server.log
    assert combat.range_command(uuid, "LONGBOWMAN", 1, s=s) in server.log  # it shoots from its AoE2 range


def test_the_war_elephant_is_a_ravager_with_its_rider():
    server, g = setup("PERSIANS", food=170, gold=85)
    rect = train.open_menu(g, "Steve", (12, 4))
    train.order(g, "Steve", rect, 0)
    uuid, = train.tick(g, 25)
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
            g.stock.update(food=170, wood=35, gold=85)
            rect, = [r for r, b in train.homes(g).items() if b == "CASTLE"]
            assert train.queue(g, "nobody", rect[::2], name)
            uuid, = train.tick(g, train.TRAIN_TIMES[name])
            assert g.pos(uuid) and g.soldiers == {uuid: name}, f"the trained {name} exists"
