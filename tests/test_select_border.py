"""game/gather.py: the border of the selection box follows the look between the two corners of the wand (#795).
Fake server; an mc test on Paper with the plugin (Border.java)."""
import json
import shutil

import pytest
from test_select_box import box
from test_select_type import setup


def paper():
    server, g = setup()
    g.paper = True
    return server, g


def test_the_first_corner_starts_the_border_in_the_player_color():
    server, g = paper()
    g.players = {"1": {"color": "red"}}
    g.box("Steve", (2, 8))
    assert "aoe box Steve 2 8 red" in server.log and "aoe box-clear Steve" not in server.log


def test_the_second_corner_ends_the_border():
    server, g = paper()
    box(g, (2, 8), (10, 18))
    log = [c for c in server.log if c.startswith("aoe box")]
    assert log == ["aoe box Steve 2 8 blue", "aoe box-clear Steve"]   # player 1 without a color in the data: blue


def test_no_border_without_the_plugin():
    server, g = setup()
    box(g, (2, 8), (10, 18))
    assert not any(c.startswith("aoe box") for c in server.log)


@pytest.mark.mc
def test_the_border_commands_work_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import gather, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        assert g.paper
        sent = []
        command = game.command
        game.command = lambda c: sent.append((c, command(c))) or sent[-1][1]
        box(g, (4, 4), (12, 12))
        answers = [out for c, out in sent if c.startswith("aoe box")]
        assert len(answers) == 2 and all(a.startswith("Box:") for a in answers), answers   # no player here: "Box: 0"
