"""game/build.py and game/train.py: a villager builds a stable, and a right click on an own stable opens its menu with
"Scout Cavalry"; a scout costs 80 food, appears after 30 AoE2 seconds and is a rider on a horse (#671)."""
import contextlib
import io
import json
import re
from urllib.parse import unquote

import pytest
from menu_line import item, labels, order
from test_gather import FakeServer, grid
from test_train_menu import RALLY

from game import build, gather, run, train

ELEPHANT = "7:gray_dye:Battle Elephant:100 food · 70 gold · 24 s · Needs the Castle Age"   # a player without a civ (#1556)
LANCER = "20:gray_dye:Steppe Lancer:70 food · 40 gold · 24 s · Needs the Castle Age"       # (#1557)
SHRIVAMSHA = "22:gray_dye:Shrivamsha Rider:70 food · 30 gold · 20 s · Needs the Castle Age"   # (#1612)
HEI_GUANG = "24:gray_dye:Hei Guang Cavalry:65 food · 65 gold · 28 s · Needs the Castle Age"   # (#1954)
XOLOTL = "26:gray_dye:Xolotl Warrior:60 food · 75 gold · 30 s · Needs the Castle Age"   # (#2009)


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
    assert stable[1] == "hay_block" and stable[3] == "175 wood\n50 s"


def test_a_right_click_on_the_stable_opens_its_menu():
    server, g = setup(done=None)
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Stable ") and labels(cmd) == order(g, "STABLE")   # the full menu
    assert [item(cmd, label) for label in ("Scout Cavalry", "Bloodlines", "Knight", "Camel Rider", "Battle Elephant",
                                           "Steppe Lancer", "Shrivamsha Rider", "Hei Guang Cavalry", "Xolotl Warrior", "Rally point")] \
        == ["0:horse_spawn_egg:Scout Cavalry:80 food · 30 s · queue 0/15", "1:book:Bloodlines:150 food · 100 gold · 50 s · research",
            "3:gray_dye:Knight:60 food · 75 gold · 30 s · Needs the Castle Age",
            "6:gray_dye:Camel Rider:55 food · 60 gold · 22 s · Needs the Castle Age", ELEPHANT, LANCER, SHRIVAMSHA, HEI_GUANG,
            XOLOTL, RALLY]


def test_no_menu_at_a_stable_that_is_not_complete():
    server, g = setup(done=False)
    assert train.open_menu(g, "Steve", (11, 3)) is None and not menus(server)


def test_a_click_queues_one_scout_and_takes_its_cost():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert rect == (10, 13, 2, 5) and train.order(g, "Steve", rect, 0) == 1
    assert g.stock["food"] == 0 and g.queues[rect][0]["name"] == "SCOUT_CAVALRY"
    assert "scoreboard players remove Food aoe_res 80" in server.log
    assert train.order(g, "Steve", rect, 0) == 0                     # no food for a second one


def test_a_shift_click_queues_5():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 0, shift=True) == 5 and g.stock["food"] == 1000 - 5 * 80
    assert item(menus(server)[-1], "Scout Cavalry").endswith(" queue 5/15")


def test_the_scout_appears_after_30_seconds_as_a_rider_on_a_horse():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 0)
    assert train.tick(g, 29) == [] and not [c for c in server.log if c.startswith("summon")]
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
        g.stock.update(food=80)
        g.techs.add("FEUDAL_AGE")
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "SCOUT_CAVALRY")
        uuid, = train.tick(g, train.TRAIN_TIMES["SCOUT_CAVALRY"])
        assert g.pos(uuid) and g.soldiers == {uuid: "SCOUT_CAVALRY"}, "the trained scout exists"
        assert "Test passed" in game.command(f"execute as {uuid} if entity @s[type=horse] on passengers "
                                             "if entity @s[type=zombie,tag=aoe2mc.p1]")
