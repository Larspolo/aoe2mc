"""game/train.py: an own archery range trains skirmishers in the Feudal Age (#730): the cost and time of the data,
and the AoE2 range of combat.STATS (combat.range_command)."""
import contextlib
import io
import json

import pytest
from test_train_archery import menus, setup
from test_train_menu import entry

from game import combat, gather, run, train

COST, TIME = train.COSTS["SKIRMISHER"], train.TRAIN_TIMES["SKIRMISHER"]


def stock(g, n=1):
    g.stock.update(food=0, wood=0, gold=0)
    g.stock.update({r: n * v for r, v in COST.items()})


def slot(g, rect):
    return train.layout(g, rect)["SKIRMISHER"][0]


def test_no_skirmisher_in_the_dark_age():
    server, g = setup()
    stock(g, 40)
    g.techs.discard("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    before = dict(g.stock)
    assert f" {entry(g, rect, 'SKIRMISHER')}{train.build.locked(g, 'SKIRMISHER')}" in menus(server)[-1]
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0 and not g.queues.get(rect) and g.stock == before


def test_a_click_queues_one_skirmisher_in_the_feudal_age():
    server, g = setup()
    stock(g)
    g.techs.add("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, slot(g, rect)) == 1 and g.queues[rect][0]["name"] == "SKIRMISHER"
    assert all(g.stock[r] == 0 for r in COST)
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0                       # no resources for a second one


def test_the_skirmisher_appears_after_its_train_time_and_shoots_from_its_range():
    server, g = setup()
    stock(g)
    g.techs.add("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, slot(g, rect))
    assert train.tick(g, TIME - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:drowned ") and "trident" in summon
    assert g.soldiers == {uuid: "SKIRMISHER"}
    assert combat.stats_command(uuid, "SKIRMISHER") in server.log      # the bonus against archers and spearmen
    assert combat.range_command(uuid, "SKIRMISHER", 1) in server.log   # the AoE2 range and reload time


@pytest.mark.mc
def test_a_trained_skirmisher_can_shoot_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo

    import aoe2mc
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
        stock(g)
        g.techs.add("FEUDAL_AGE")
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "SKIRMISHER")
        uuid, = train.tick(g, train.TRAIN_TIMES["SKIRMISHER"])
        assert g.pos(uuid) and g.soldiers == {uuid: "SKIRMISHER"}, "the trained skirmisher exists"
        # the plugin takes a range only for a mob that can shoot: the drowned throws its trident
        assert "Range: 1 units" in game.command(combat.range_command(uuid, "SKIRMISHER", data["tile_size"]))
