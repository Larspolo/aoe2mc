"""game/train.py: a right click on an own barracks opens its menu with "Militia"; a militia costs 60 food and 20 gold,
appears after 21 AoE2 seconds and joins the military units of the player (#654)."""
import contextlib
import io
import json
import re
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid
from test_train_menu import FEUDAL, RALLY

from game import combat, gather, run, train


def setup(food=60, gold=20, done=True):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, a barracks at x 10-12,
    z 2-4 (a start one, or a built site when done is a bool) and a villager. Steve stands south of the barracks."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    if done is None:
        objects.append({"kind": "building", "name": "BARRACKS", "player": 1, "tile": [11.5, 3.5],
                        "footprint": [10, 2, 13, 5]})
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "Steve": {"Pos": (11.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    if done is not None:
        g.sites.append({"name": "BARRACKS", "player": 1, "footprint": [10, 13, 2, 5], "done": done})
    g.stock.update(food=food, gold=gold)
    server.scores["aoe_use"] = 1
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_a_right_click_on_the_barracks_opens_its_menu():
    server, g = setup(done=None)
    for name in g.clicks():
        g.click(name)
    assert menus(server) == ["aoe menu Steve Barracks 0:zombie_spawn_egg:Militia:60 food · 20 gold · 21 s · queue 0/15" + RALLY]
    assert not any(g.queues.values())


def test_the_town_center_menu_does_not_change():
    server, g = setup()
    train.open_menu(g, "Steve", (3, 3))
    assert menus(server) == ["aoe menu Steve Town Center 0:villager_spawn_egg:Villager:50 food · 25 s · queue 0/15 "
                             "1:book:Loom:50 gold · 25 s · research" + FEUDAL.replace("0/2", "1/2") + RALLY]   # the barracks


def test_no_menu_at_a_barracks_that_is_not_complete():
    server, g = setup(done=False)
    assert train.open_menu(g, "Steve", (11, 3)) is None and not menus(server)


def test_a_click_queues_one_militia_and_takes_its_cost():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert rect == (10, 13, 2, 5) and train.order(g, "Steve", rect, 0) == 1
    assert g.stock["food"] == 0 and g.stock["gold"] == 0 and g.queues[rect][0]["name"] == "MILITIA"
    assert "scoreboard players remove Gold aoe_res 20" in server.log
    assert train.order(g, "Steve", rect, 0) == 0 and any("20 gold" in c for c in server.log if c.startswith("tellraw"))
    assert train.queue(g, "Steve", (11, 3)) is None                    # a barracks trains no villager


def test_a_shift_click_queues_as_many_as_the_stock_allows():
    server, g = setup(food=1000, gold=70)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 0, shift=True) == 3 and g.stock["gold"] == 10
    assert menus(server)[-1].endswith("queue 3/15" + RALLY)


def test_the_militia_appears_after_21_seconds_and_joins_the_military_units():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 0)
    assert train.tick(g, 20) == [] and not [c for c in server.log if c.startswith("summon")]
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    m = re.match(r"summon minecraft:zombie (\S+) (\S+) (\S+) ", summon)
    assert m and (float(m[1]), float(m[2]), float(m[3])) == (11.5, 64.0, 5.5)  # south of the middle
    assert g.soldiers == {uuid: "MILITIA"} and set(g.villagers) == {"v"}
    assert any(c.startswith(f"aoe stats {uuid} ") for c in server.log)  # the AoE2 hit points
    server.entities[uuid] = {"Pos": (11.5, 64.0, 5.5)}
    train.census(g)
    assert g.pop == 2                                                  # it counts for the population


@pytest.mark.mc
def test_a_trained_militia_exists_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.BARRACKS.ID, x=4.5, y=4.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.HOUSE.ID, x=11, y=11)   # population 5
    src = str(tmp_path / "barracks.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25).setup()
        g.stock.update(food=60, gold=20)
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "MILITIA")
        uuid, = train.tick(g, train.TRAIN_TIMES["MILITIA"])
        assert g.pos(uuid) and g.soldiers == {uuid: "MILITIA"}, "the trained militia exists"
        assert "Stats: 1 units" in game.command(combat.stats_command(uuid, "MILITIA"))
