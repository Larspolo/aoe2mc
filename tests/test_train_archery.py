"""game/build.py and game/train.py: a villager builds an archery range, and a right click on an own archery range opens
its menu with "Archer"; an archer takes its cost, appears after its AoE2 train time and shoots from its AoE2 range
(#670)."""
import contextlib
import io
import json
import re

import pytest
from menu_line import item, labels, order
from test_forging import menus                                         # a long menu: with its `aoe menu-add` parts
from test_gather import FakeServer, grid
from test_train_menu import check_items

from game import build, combat, gather, run, train


def setup(wood=25, gold=45, done=True):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, an archery range at x 10-12,
    z 2-4 (a start one, or a built site when done is a bool) and a villager. Steve stands south of the range."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    if done is None:
        objects.append({"kind": "building", "name": "ARCHERY_RANGE", "player": 1, "tile": [11.5, 3.5],
                        "footprint": [10, 2, 13, 5]})
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "Steve": {"Pos": (11.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    if done is not None:
        g.sites.append({"name": "ARCHERY_RANGE", "player": 1, "footprint": [10, 13, 2, 5], "done": done})
    g.stock.update(wood=wood, gold=gold)
    g.techs.add("FEUDAL_AGE")                                          # archers are a Feudal Age unit (#674)
    server.scores["aoe_use"] = 1
    return server, g


COST, TIME = train.COSTS["ARCHER"], train.TRAIN_TIMES["ARCHER"]


def test_the_build_menu_has_the_archery_range():
    archery, = [i for i in build.items() if i[2] == "Archery Range"]
    assert archery[1] == build.ICONS["ARCHERY_RANGE"]


def test_a_right_click_on_the_archery_range_opens_its_menu():
    server, g = setup(done=None)
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Archery Range ") and labels(cmd) == order(g, "ARCHERY_RANGE")   # the full menu
    check_items(g, (10, 13, 2, 5), cmd)


def test_no_menu_at_an_archery_range_that_is_not_complete():
    server, g = setup(done=False)
    assert train.open_menu(g, "Steve", (11, 3)) is None and not menus(server)


def slot(g, rect):
    return train.layout(g, rect)["ARCHER"][0]


def test_a_click_queues_one_archer_and_takes_its_cost():
    server, g = setup(wood=COST.get("wood", 0), gold=COST.get("gold", 0))
    rect = train.open_menu(g, "Steve", (11, 3))
    assert rect == (10, 13, 2, 5) and train.order(g, "Steve", rect, slot(g, rect)) == 1
    assert g.stock["wood"] == 0 and g.stock["gold"] == 0 and g.queues[rect][0]["name"] == "ARCHER"
    assert all(f"scoreboard players remove {r.capitalize()} aoe_res {v}" in server.log for r, v in COST.items())
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0         # no wood and gold for a second one


def test_a_shift_click_queues_5():
    server, g = setup(wood=1000, gold=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, slot(g, rect), shift=True) == 5
    assert all(g.stock[r] == 1000 - 5 * v for r, v in COST.items())
    assert item(menus(server)[-1], train.ITEMS["ARCHER"][2]).endswith(" queue 5/15")


def test_the_archer_appears_after_its_train_time_and_shoots_from_its_range():
    server, g = setup(wood=COST.get("wood", 0), gold=COST.get("gold", 0))
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, slot(g, rect))
    assert train.tick(g, TIME - 1) == [] and not [c for c in server.log if c.startswith("summon")]
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:skeleton 11.5 64.0 5.5 ", summon)
    assert g.soldiers == {uuid: "ARCHER"}
    assert combat.range_command(uuid, "ARCHER", 1) in server.log      # the AoE2 range and reload time


@pytest.mark.mc
def test_a_trained_archer_can_shoot_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.ARCHERY_RANGE.ID, x=4.5, y=4.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.HOUSE.ID, x=11, y=11)   # population 5
    src = str(tmp_path / "range.aoe2scenario")
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
        assert train.queue(g, "nobody", rect[::2], "ARCHER")
        uuid, = train.tick(g, train.TRAIN_TIMES["ARCHER"])
        assert g.pos(uuid) and g.soldiers == {uuid: "ARCHER"}, "the trained archer exists"
        assert "Range: 1 units" in game.command(combat.range_command(uuid, "ARCHER", data["tile_size"]))
