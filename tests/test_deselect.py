"""game/gather.py: on Paper a left click with the command stick clears the selection (#1788). The plugin
(AoePlugin.onLeftClick) sets the score aoe_left; Gather.clicks reads it."""
import shutil

import pytest
from test_select_type import setup

from game import gather, hints


def paper():
    server, g = setup()
    g.paper = True                                                     # after setup: no plugin commands to the fake
    return server, g


def test_a_left_click_clears_the_selection():
    server, g = paper()
    g.select("m-1")
    server.scores[gather.LEFT] = 1
    assert g.clicks() == []                                            # no right click: no ray, no order
    assert g.selected == set() and g.bar is None
    assert f"tag m-1 remove {gather.SELECT}" in server.log and gather.LEFT not in server.scores


def test_no_left_click_keeps_the_selection():
    server, g = paper()
    g.select("m-1")
    g.clicks()
    assert g.selected == {"m-1"}


def test_vanilla_reads_no_left_click():
    server, g = setup()
    g.select("m-1")
    server.scores[gather.LEFT] = 1
    g.clicks()
    assert g.selected == {"m-1"} and not any(gather.LEFT in c for c in server.log)


def test_the_hint_names_the_left_click_on_paper():
    _, g = paper()
    g.select("m-1")
    assert "Left click: deselect" in hints.state(g)[1] and "Empty box" not in hints.state(g)[1]
    g.paper = False
    assert "Empty box: deselect" in hints.state(g)[1]


@pytest.mark.mc
def test_a_left_click_deselects_on_paper(tiny_world, tmp_path):
    """A real client on Paper with the plugin left clicks with the command stick on a unit, a block and the air: each
    click clears the selection, breaks no block and does no damage. A left click with a control group item does not."""
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import json
    import time

    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(5)                                                  # the world is drawn
        game.forceload()
        g = gather.Gather(game, data).setup()
        assert g.paper
        v = next(iter(g.villagers.values()))
        for c in ("forceload add 0 0", "fill -2 99 -2 2 99 4 stone", "fill -2 100 -2 2 103 4 air",
                  'summon villager 0.5 100 2.5 {NoAI:1b,Tags:["t1788"],Health:20f}',
                  "item replace entity aoe2mc hotbar.0 with minecraft:carrot_on_a_stick"):
            game.command(c)
        client.key("1")

        def left(look, item=None):
            if item:
                game.command(f"item replace entity aoe2mc hotbar.0 with {item}")
            game.command(f"tp aoe2mc 0.5 100 0.5 {look}")
            time.sleep(1.5)
            g.choose({v.uuid}, v.uuid)
            client.xdo("click", "1")
            time.sleep(1.5)
            g.clicks()
            return g.selected
        assert left("0 15") == set()                                   # the villager in front
        assert "20.0f" in game.command("data get entity @e[tag=t1788,limit=1] Health")
        assert left("0 90") == set()                                   # the stone under the feet
        assert "passed" in game.command("execute if block 0 99 0 minecraft:stone")
        assert left("0 -90") == set()                                  # the air
        assert left("0 -90", gather.group_item(1)) == {v.uuid}       # a control group item keeps the selection
        client.shot(str(tmp_path / "left.png"))
