"""game/train.py: an own archery range trains skirmishers in the Feudal Age (#730): 25 food and 35 wood, 22 AoE2
seconds, and the AoE2 range of combat.STATS (combat.range_command)."""
import contextlib
import io
import json

import pytest
from test_train_archery import menus, setup

from game import combat, gather, run, train


def stock(g, food=25, wood=35):
    g.stock.update(food=food, wood=wood)


def test_no_skirmisher_in_the_dark_age():
    server, g = setup()
    stock(g, 1000, 1000)
    g.techs.discard("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    assert "1:gray_dye:Skirmisher:25 food · 35 wood · 22 s · Needs the Feudal Age" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 1) == 0 and not g.queues.get(rect) and g.stock["wood"] == 1000


def test_a_click_queues_one_skirmisher_in_the_feudal_age():
    server, g = setup()
    stock(g)
    g.techs.add("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 1) == 1 and g.queues[rect][0]["name"] == "SKIRMISHER"
    assert g.stock["food"] == 0 and g.stock["wood"] == 0
    assert train.order(g, "Steve", rect, 1) == 0                       # no resources for a second one


def test_the_skirmisher_appears_after_22_seconds_and_shoots_from_its_range():
    server, g = setup()
    stock(g)
    g.techs.add("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 1)
    assert train.tick(g, 21) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:drowned ") and "trident" in summon
    assert g.soldiers == {uuid: "SKIRMISHER"}
    assert combat.stats_command(uuid, "SKIRMISHER") in server.log      # the bonus against archers and spearmen
    assert combat.range_command(uuid, "SKIRMISHER", 1) in server.log   # the AoE2 range 4 and reload time


@pytest.mark.mc
def test_a_trained_skirmisher_can_shoot_on_a_server(tmp_path):
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
        g = gather.Gather(game, data, tick=0.25).setup()
        stock(g)
        g.techs.add("FEUDAL_AGE")
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "SKIRMISHER")
        uuid, = train.tick(g, train.TRAIN_TIMES["SKIRMISHER"])
        assert g.pos(uuid) and g.soldiers == {uuid: "SKIRMISHER"}, "the trained skirmisher exists"
        # the plugin takes a range only for a mob that can shoot: the drowned throws its trident
        assert "Range: 1 units" in game.command(combat.range_command(uuid, "SKIRMISHER", data["tile_size"]))
