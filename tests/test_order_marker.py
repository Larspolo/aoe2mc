"""game/gather.py: an order shows a short marker at its target, as the flag of AoE2 (#796): a ring of dust on the
ground for a gather, build or building attack order, the glowing effect for 1 second on an attacked unit."""
import json
import math
import re
import shutil

import pytest
import test_gather_attack
import test_gather_select
from test_gather_attack import click

from game import gather


def rings(log):
    """The dust points of the order markers in log: [(color, x, y, z)]."""
    return [(m[1], float(m[2]), float(m[3]), float(m[4])) for c in log
            if (m := re.fullmatch(r"particle minecraft:dust\{color:(\S+),scale:1\.5\} (\S+) (\S+) (\S+) 0 0 0 0 1 "
                                  r"force Steve", c))]


def look(server, g, at, ground):
    """Steve stands 2 blocks above the ground at block at and clicks the ground point ground (x, z)."""
    eye = (at[0], 66.0 + 1.62, at[1])
    dx, dz, dy = ground[0] - eye[0], ground[1] - eye[2], 64 - eye[1]
    yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    server.entities["Steve"] = {"Pos": (at[0], 66.0, at[1]), "Rotation": (yaw, pitch)}
    server.log.clear()
    g.click("Steve")
    return server.log


def test_a_gather_order_shows_a_green_ring_around_the_tree():
    g = test_gather_select.setup()
    server, g.selected = g.game, {"v"}
    log = click(server, g, (20.5, 9.5), (20.5, 4.5))
    assert g.villagers["v"].tree == (20, 4)
    pts = rings(log)
    assert len(pts) == gather.MARK_POINTS and {p[0] for p in pts} == {gather.MARK["go"]}
    assert all(abs(((x - 20.5) ** 2 + (z - 4.5) ** 2) ** 0.5 - 1) < 0.01 and y == 64.2 for _, x, y, z in pts)


def test_a_build_order_shows_a_ring_around_the_site():
    g = test_gather_select.setup()
    server, g.selected = g.game, {"v"}
    g.sites = [{"name": "HOUSE", "footprint": [9, 11, 18, 20], "progress": 0}]
    log = look(server, g, (10.0, 23.5), (10.0, 19.5))
    assert g.villagers["v"].state == "to_site"
    pts = rings(log)
    assert len(pts) == gather.MARK_POINTS
    assert all(abs(((x - 10) ** 2 + (z - 19) ** 2) ** 0.5 - 1.5) < 0.01 for _, x, _, z in pts)


def test_an_attack_on_a_unit_makes_it_glow_for_1_second():
    server, g = test_gather_attack.setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))                         # select the militia
    log = click(server, g, (10.5, 17.5), (10.5, 14.5))
    assert "effect give foe minecraft:glowing 1 0 true" in log
    assert log.index("aoe attack @e[tag=aoe2mc.selected] foe") < log.index("effect give foe minecraft:glowing 1 0 true")
    assert not rings(log)


def test_an_attack_on_a_building_shows_a_red_ring():
    server, g = test_gather_attack.setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    g.forts["fort"] = (14, 64, 2, 17, 70, 5)
    log = click(server, g, (15.5, 9.5), (15.5, 4.0))
    assert "aoe attack @e[tag=aoe2mc.selected] fort" in log
    pts = rings(log)
    assert len(pts) == gather.MARK_POINTS and {p[0] for p in pts} == {gather.MARK["attack"]}


def test_a_selection_click_shows_no_marker():
    server, g = test_gather_attack.setup()
    log = click(server, g, (5.5, 13.5), (5.5, 10.5))
    assert not rings(log) and not [c for c in log if c.startswith("effect give")]


@pytest.mark.mc
def test_the_marker_commands_work_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        game.command("summon minecraft:armor_stand 8 80 8 {NoGravity:1b,Tags:[\"foe\"]}")
        answers = []
        g.command = lambda c: answers.append(game.command(c))
        g.mark("@a", {(8, 8), (11, 11)})                                # no client here: no player sees it
        g.mark("@a", {(8, 8)}, "attack")
        answers.append(game.command("effect give @e[tag=foe,limit=1] minecraft:glowing 1 0 true"))
        assert len(answers) == 2 * gather.MARK_POINTS + 1
        assert all("<--[HERE]" not in a and "Unknown" not in a for a in answers), answers
        assert answers[-1].startswith("Applied effect"), answers[-1]
