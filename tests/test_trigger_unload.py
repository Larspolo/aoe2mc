"""#2773 (epic #2538): the trigger effect "Unload" lets the garrison of the selected buildings out. The converter puts
the order "unload <player> <ref> x y z" into the data storage aoe2mc:orders; the scenario mode of the game program
lets the units out (garrison.out) and walks them to the target with `aoe moveto`."""
import contextlib
import io
from collections import Counter

import numpy as np
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from test_garrison_game import TC, setup

import aoe2mc
import buildings
from game import scenario
from tools import scenarios

FN = "data/aoe2mc/function/trigger/0.mcfunction"
STORED = "Storage aoe2mc:orders has the following contents: "


def test_scenario_effect_stores_the_unload_of_the_castle(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")))
    castle = scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.CASTLE.ID, x=8, y=8)
    t = scn.trigger_manager.add_trigger("Out")
    t.new_condition.timer(timer=5)
    t.new_effect.unload(source_player=1, location_x=3, location_y=2, selected_object_ids=[castle.reference_id])
    path = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    trig, = aoe2mc.read_scenario(path)[4]["triggers"]
    assert trig["effects"][0]["selected"] == [castle.reference_id]
    buildings.INSIDE[castle.reference_id] = ([(33, 34)], 70, (34, 34))
    stats = Counter()
    try:
        _, files = aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16), stats=stats)
    finally:
        del buildings.INSIDE[castle.reference_id]
    assert f'data modify storage aoe2mc:orders list append value "unload 1 {castle.reference_id} 14 70 10"' \
        in files[FN].splitlines()
    assert stats["unload"] == 1


def test_with_no_selection_it_unloads_the_buildings_in_the_area():
    e = dict(type=aoe2mc.UNLOAD, player=2, tile=[-1, -1], area=[8, 8, 9, 9], selected=[])
    c = aoe2mc.Effect(dict(id=0, effects=[e]), 4, None, {}, Counter(), True, {}, [])
    buildings.INSIDE.update({987001: ([], 70, (34, 34)), 987002: ([], 70, (50, 34))})
    try:
        assert aoe2mc.unload_lines(e, c) == ['data modify storage aoe2mc:orders list append value "unload 2 987001"']
    finally:
        del buildings.INSIDE[987001], buildings.INSIDE[987002]


def test_a_holder_that_is_no_building_is_not_supported():
    e = dict(type=aoe2mc.UNLOAD, player=1, tile=[3, 2], area=[-1] * 4, selected=[987654])
    c = aoe2mc.Effect(dict(id=0, effects=[e]), 4, None, {}, Counter(), True, {}, [])
    assert aoe2mc.unload_lines(e, c) == [] and c.stats["unload (not supported yet)"] == 1


def unload(order):
    """Run scenario.orders once with the order in the storage; the town center (ref 1) holds v0 and v1."""
    server, g = setup(villagers=2)
    g.garrisons[TC] = ["v0", "v1"]
    command = server.command

    def answer(cmd):
        if cmd.startswith("data get storage aoe2mc:orders"):
            server.log.append(cmd)
            return STORED + f'["{order}"]'
        return command(cmd)
    server.command = answer
    scenario.orders(g)
    return server, g


def test_the_units_come_out_of_the_town_center_and_walk_to_the_target():
    server, g = unload("unload 1 1 14 64 10")
    assert TC not in g.garrisons
    assert "data remove storage aoe2mc:orders list" in server.log
    for u in ("v0", "v1"):
        assert f"tag {u} remove aoe2mc.garrisoned" in server.log
        assert server.log.index(f"aoe moveto {u} 14 64 10") > server.log.index(f"tag {u} remove aoe2mc.garrisoned")


def test_the_holder_of_another_player_keeps_its_units():
    server, g = unload("unload 2 1 14 64 10")
    assert g.garrisons[TC] == ["v0", "v1"]
    assert not [c for c in server.log if c.startswith("aoe moveto")]
