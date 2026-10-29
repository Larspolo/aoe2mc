"""game/train.py: a right click on an own barracks opens its menu with "Militia"; a militia takes its cost,
appears after its AoE2 train time and joins the military units of the player (#654)."""
import contextlib
import io
import json
import re

import pytest
from menu_line import item, labels, order
from test_forging import menus                                         # also the `aoe menu-add` parts (#1647)
from test_gather import FakeServer, grid
from test_train_menu import check_items

from game import combat, gather, run, train

COST, TIME = train.COSTS["MILITIA"], train.TRAIN_TIMES["MILITIA"]


def setup(food=50, gold=20, done=True):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, a barracks at x 10-12,
    z 2-4 (a start one, or a built site when done is a bool) and a villager. Steve stands south of the barracks."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    if done is None:
        objects.append({"kind": "building", "name": "BARRACKS", "player": 1, "tile": [11.5, 3.5],
                        "footprint": [10, 2, 13, 5]})
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "Steve": {"Pos": (11.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    if done is not None:
        g.sites.append({"name": "BARRACKS", "player": 1, "footprint": [10, 13, 2, 5], "done": done})
    g.stock.update(food=food, gold=gold)
    server.scores["aoe_use"] = 1
    return server, g


def test_a_right_click_on_the_barracks_opens_its_menu():
    server, g = setup(done=None)
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    full = order(g, "BARRACKS")                                        # a long menu goes in parts, the last slot first
    assert cmd.startswith("aoe menu Steve Barracks ") and labels(cmd) in (full, sorted(full, key=lambda s: -s[0]))   # (menu.commands, #2483)
    check_items(g, (10, 13, 2, 5), cmd)
    assert not any(g.queues.values())


def test_the_town_center_menu_does_not_change():
    server, g = setup()
    train.open_menu(g, "Steve", (3, 3))
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Town Center ") and labels(cmd) == order(g, "TOWN_CENTER")
    assert item(cmd, train.ITEMS["FEUDAL_AGE"][2]).endswith(" (1/2)")   # the barracks counts for the Feudal Age


def test_no_menu_at_a_barracks_that_is_not_complete():
    server, g = setup(done=False)
    assert train.open_menu(g, "Steve", (11, 3)) is None and not menus(server)


def slot(g, rect):
    return train.layout(g, rect)["MILITIA"][0]


def test_a_click_queues_one_militia_and_takes_its_cost():
    server, g = setup(food=COST.get("food", 0), gold=COST.get("gold", 0))
    rect = train.open_menu(g, "Steve", (11, 3))
    assert rect == (10, 13, 2, 5) and train.order(g, "Steve", rect, slot(g, rect)) == 1
    assert g.stock["food"] == 0 and g.stock["gold"] == 0 and g.queues[rect][0]["name"] == "MILITIA"
    assert all(f"scoreboard players remove {r.capitalize()} aoe_res {v}" in server.log for r, v in COST.items())
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0
    assert any(f"{v} {r}" in c for c in server.log if c.startswith("tellraw") for r, v in COST.items())
    assert train.queue(g, "Steve", (11, 3)) is None                    # a barracks trains no villager


def test_a_shift_click_queues_as_many_as_the_stock_allows():
    gold = COST["gold"]
    server, g = setup(food=1000 * COST.get("food", 1), gold=3 * gold + gold // 2)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, slot(g, rect), shift=True) == 3 and g.stock["gold"] == gold // 2
    assert item(menus(server)[-1], train.ITEMS["MILITIA"][2]).endswith(" queue 3/15")


def test_the_militia_appears_after_its_train_time_and_joins_the_military_units():
    server, g = setup(food=COST.get("food", 0), gold=COST.get("gold", 0))
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, slot(g, rect))
    assert train.tick(g, TIME - 1) == [] and not [c for c in server.log if c.startswith("summon")]
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
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.stock.update(COST)
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "MILITIA")
        uuid, = train.tick(g, train.TRAIN_TIMES["MILITIA"])
        assert g.pos(uuid) and g.soldiers == {uuid: "MILITIA"}, "the trained militia exists"
        assert "Stats: 1 units" in game.command(combat.stats_command(uuid, "MILITIA"))
