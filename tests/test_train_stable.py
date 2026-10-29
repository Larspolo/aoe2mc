"""game/build.py and game/train.py: a villager builds a stable, and a right click on an own stable opens its menu with
"Scout Cavalry"; a scout takes its cost, appears after its AoE2 train time and is a rider on a horse (#671)."""
import contextlib
import io
import json
import re
from urllib.parse import unquote

import pytest
from menu_line import item, labels, order
from test_gather import FakeServer, grid
from test_train_menu import check_items

from game import build, gather, run, train

COST, TIME = train.COSTS["SCOUT_CAVALRY"], train.TRAIN_TIMES["SCOUT_CAVALRY"]


def setup(food=80, done=True):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, a stable at x 10-12,
    z 2-4 (a start one, or a built site when done is a bool) and a villager. Steve stands south of the stable."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    if done is None:
        objects.append({"kind": "building", "name": "STABLE", "player": 1, "tile": [11.5, 3.5],
                        "footprint": [10, 2, 13, 5]})
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "Steve": {"Pos": (11.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    if done is not None:
        g.sites.append({"name": "STABLE", "player": 1, "footprint": [10, 13, 2, 5], "done": done})
    g.stock.update(food=food)
    g.techs.add("FEUDAL_AGE")                                          # scouts are a Feudal Age unit (#674)
    server.scores["aoe_use"] = 1
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_build_menu_has_the_stable():
    stable, = [i for i in build.items() if i[2] == "Stable"]
    assert stable[1] == build.ICONS["STABLE"]


def test_a_right_click_on_the_stable_opens_its_menu():
    server, g = setup(done=None)
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Stable ") and labels(cmd) == order(g, "STABLE")   # the full menu
    check_items(g, (10, 13, 2, 5), cmd)


def test_no_menu_at_a_stable_that_is_not_complete():
    server, g = setup(done=False)
    assert train.open_menu(g, "Steve", (11, 3)) is None and not menus(server)


def slot(g, rect):
    return train.layout(g, rect)["SCOUT_CAVALRY"][0]


def test_a_click_queues_one_scout_and_takes_its_cost():
    server, g = setup(food=COST["food"])
    rect = train.open_menu(g, "Steve", (11, 3))
    assert rect == (10, 13, 2, 5) and train.order(g, "Steve", rect, slot(g, rect)) == 1
    assert g.stock["food"] == 0 and g.queues[rect][0]["name"] == "SCOUT_CAVALRY"
    assert f"scoreboard players remove Food aoe_res {COST['food']}" in server.log
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0         # no food for a second one


def test_a_shift_click_queues_5():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, slot(g, rect), shift=True) == 5 and g.stock["food"] == 1000 - 5 * COST["food"]
    assert item(menus(server)[-1], train.ITEMS["SCOUT_CAVALRY"][2]).endswith(" queue 5/15")


def test_the_scout_appears_after_its_train_time_as_a_rider_on_a_horse():
    server, g = setup(food=COST["food"])
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, slot(g, rect))
    assert train.tick(g, TIME - 1) == [] and not [c for c in server.log if c.startswith("summon")]
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:horse 11.5 64.0 6.5 ", summon)   # one cell out: the rider sits back (#767)
    flat = re.sub(r"\s", "", summon)
    assert "Passengers:[{" in flat and "minecraft:zombie" in flat and 'Tags:["aoe2mc.p1","aoe2mc.t448"]' in flat   # the rider
    assert g.soldiers == {uuid: "SCOUT_CAVALRY"}


@pytest.mark.mc
def test_a_trained_scout_is_a_rider_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.STABLE.ID, x=4.5, y=4.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.HOUSE.ID, x=11, y=11)   # population 5
    src = str(tmp_path / "stable.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.stock.update(COST)
        g.techs.add("FEUDAL_AGE")
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "SCOUT_CAVALRY")
        uuid, = train.tick(g, train.TRAIN_TIMES["SCOUT_CAVALRY"])
        assert g.pos(uuid) and g.soldiers == {uuid: "SCOUT_CAVALRY"}, "the trained scout exists"
        assert "Test passed" in game.command(f"execute as {uuid} if entity @s[type=horse] on passengers "
                                             "if entity @s[type=zombie,tag=aoe2mc.p1]")
