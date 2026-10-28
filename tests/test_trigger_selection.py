"""Triggers stop and allow again the selection of the units of a player in an area (#2854): the entity tag
aoe2mc.UNSELECTABLE. The scenario mode of the game program reads the tagged units, and no click, box or double click
selects them."""
import numpy as np

import aoe2mc
from game import scenario, stance

from test_gather_attack import click
from test_select_type import setup


def effect(type, area=(1, 2, 2, 3), player=1):
    return dict(type=type, message="", player=player, time=0, object=None, tile=[-1, -1], area=list(area))


def lines(effects, T=4):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_disable_tags_the_units_in_the_area_and_enable_removes_the_tag():
    sel = aoe2mc.unit_selector(effect(0), 4)
    assert lines([effect(aoe2mc.DISABLE_OBJECT_SELECTION)]) == [f"tag {sel} add {aoe2mc.UNSELECTABLE}"]
    assert lines([effect(aoe2mc.ENABLE_OBJECT_SELECTION)]) == [f"tag {sel} remove {aoe2mc.UNSELECTABLE}"]
    assert scenario.UNSELECTABLE == aoe2mc.UNSELECTABLE


def test_gaia_units_and_no_area():
    assert "type=!player" in lines([effect(aoe2mc.DISABLE_OBJECT_SELECTION, player=0)])[0]
    assert lines([effect(aoe2mc.DISABLE_OBJECT_SELECTION, area=(-1, -1, -1, -1))]) == []


def tagged(g, uuids):
    """The scenario check on Paper: `aoe where` finds the units with the tag."""
    g.paper, asked = True, []
    g.where = lambda want, sel: asked.append(sel) or {u: (0.0, 64.0, 0.0) for u in uuids}
    scenario.selection(g)
    assert asked == [f"@e[tag={aoe2mc.UNSELECTABLE}]"]


def test_a_click_on_a_tagged_unit_selects_nothing():
    server, g = setup()
    tagged(g, {"m-1", "v-1"})
    click(server, g, (5.5, 13.5), (5.5, 10.5))                         # the militia m-1
    click(server, g, (12.5, 7.5), (12.5, 4.5))                         # the villager v-1
    assert not g.selected
    tagged(g, set())                                                   # "Enable Object Selection"
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    assert g.selected == {"m-1"}


def test_a_box_and_a_double_click_skip_a_tagged_unit():
    server, g = setup()
    tagged(g, {"m-2"})
    g.box("Steve", (2, 8))
    g.box("Steve", (10, 18))
    assert g.selected == {"m-1", "m-3", "a-1"}                         # not m-2
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    g.menus["Steve"]("Steve", stance.TYPE, False)                      # all militia near m-1
    assert g.selected == {"m-1", "m-3"}


def test_a_selected_unit_that_gets_the_tag_leaves_the_selection():
    server, g = setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    assert g.selected == {"m-1"}
    tagged(g, {"m-1"})
    assert not g.selected and "data merge entity m-1 {Glowing:0b}" in server.log


def test_vanilla_reads_no_tags():
    _, g = setup()
    scenario.selection(g)
    assert "unselectable" not in vars(g)
