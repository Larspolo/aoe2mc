"""game/gather.py: the selection wand selects the own units in a box of two corners (#778, owner choice #745)."""
import shutil

import pytest
from test_gather_attack import click
from test_select_type import setup

from game import gather


def box(g, a, b):
    g.box("Steve", a)
    return g.box("Steve", b)


def test_two_corners_select_the_military_units_in_the_box():
    server, g = setup()
    g.box("Steve", (2, 8))
    assert g.corners == {"Steve": (2, 8)} and not g.selected
    assert any(c.startswith("particle minecraft:happy_villager 2.5 ") and c.endswith("force Steve") for c in server.log)
    g.box("Steve", (10, 18))
    assert g.selected == {"m-1", "m-2", "m-3", "a-1"}                  # not the far militia, not the villager v-1
    assert not g.corners and all(f"tag {u} add {gather.SELECT}" in server.log for u in g.selected)
    assert 'title Steve actionbar {"text": "Selected: 4 units"}' in server.log


def test_the_corners_can_be_in_any_order():
    _, g = setup()
    box(g, (10, 18), (2, 8))
    assert g.selected == {"m-1", "m-2", "m-3", "a-1"}


def test_a_box_with_only_villagers_selects_them():
    _, g = setup()
    box(g, (11, 3), (13, 5))
    assert g.selected == {"v-1"}


def test_units_outside_the_box_leave_the_selection():
    server, g = setup()
    g.select("v-1")
    server.log.clear()
    box(g, (5, 10), (5, 10))                                           # one cell: the militia m-1
    assert g.selected == {"m-1"}
    assert f"tag v-1 remove {gather.SELECT}" in server.log and "data merge entity v-1 {Glowing:0b}" in server.log
    assert g.bar == "m-1"


def test_an_empty_box_clears_the_selection():
    _, g = setup()
    g.select("m-1")
    box(g, (20, 20), (25, 25))
    assert g.selected == set() and g.bar is None


def test_a_wand_click_sets_a_corner_on_the_ground():
    server, g = setup()
    server.scores["aoe_box"] = 1
    assert g.clicks() == ["Steve"] and g.wands == {"Steve"}
    assert any("give @s minecraft:warped_fungus_on_a_stick" in c for c in server.log)
    click(server, g, (5.5, 20.5), (5.5, 14.5))                         # no unit is picked: the wand wins
    assert not g.wands and g.corners["Steve"][0] == 5 and not g.selected


@pytest.mark.mc
def test_the_wand_commands_work_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import json

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        sent = []
        command = game.command
        game.command = lambda c: sent.append((c, command(c))) or sent[-1][1]
        g.clicks()
        v, = g.villagers.values()
        x, z = map(int, v.cell)
        box(g, (x - 2, z - 2), (x + 2, z + 2))
        assert g.selected == {v.uuid}
        bad = [(c, out) for c, out in sent if any(w in out for w in ("Unknown", "Incorrect", "Invalid", "Expected", "Failed to parse"))]
        assert not bad, bad
