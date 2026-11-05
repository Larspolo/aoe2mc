"""game/gather.py: on Paper a held left click with the command stick draws the selection box (Drag.java, #5759). The
plugin sets the score aoe_left 2 and answers "aoe drag PLAYER" with the corners; a right click gives its order at once."""
import json
import shutil
import time

import pytest
from test_deselect import paper
from test_left_click import left

from game import gather


def drag(server, g, corners):
    """The plugin ended a drag of Steve with these corners (x0 z0 x1 z1)."""
    answer = server.command
    server.command = lambda c: f"Drag: {corners}" if c == "aoe drag Steve" else answer(c)
    server.scores[gather.LEFT] = 2
    server.log.clear()
    return g.clicks()


def test_a_drag_selects_the_military_units_in_the_box():
    server, g = paper()
    assert drag(server, g, "2 8 13 13") == []                          # m-1, m-2, a-1 and v-1: no order
    assert g.selected == {"m-1", "m-2", "a-1"} and gather.LEFT not in server.scores


def test_a_drag_over_villagers_only_selects_them():
    server, g = paper()
    assert drag(server, g, "14 2 10 6") == [] and g.selected == {"v-1"}   # the corners in any order


def test_an_empty_drag_clears_the_selection():
    server, g = paper()
    g.select("m-1")
    drag(server, g, "20 20 25 25")
    assert g.selected == set()


def test_no_corners_change_nothing():
    server, g = paper()
    g.select("m-1")
    drag(server, g, "none")
    assert g.selected == {"m-1"}


def test_a_drag_of_less_than_one_block_is_a_click():
    server, g = paper()                                                # the plugin sets the score 1 (Drag.tick)
    left(server, g, (5.5, 13.5), (5.5, 10.5))
    assert g.selected == {"m-1"} and "aoe drag Steve" not in server.log


def test_a_right_click_on_the_ground_orders_at_once():
    server, g = paper()
    g.select("m-1")
    server.entities["Steve"] = {"Pos": (20.5, 64.0, 30.5), "Rotation": (0.0, 45.0)}
    server.scores["aoe_use"] = 1
    assert g.clicks() == ["Steve"] and not g.corners                   # the same call: no wait, no box


def test_a_right_click_on_an_own_unit_does_not_select_on_paper():
    server, g = paper()                                                # the left click selects (#5759)
    left(server, g, (5.5, 13.5), (5.5, 10.5))
    server.scores.pop(gather.LEFT, None)
    g.choose(set())
    server.scores["aoe_use"] = 1
    g.clicks()
    assert g.selected == set()


@pytest.mark.mc
def test_a_real_left_drag_selects_the_box(tiny_world, tmp_path):
    """A real client on Paper holds the left button with the command stick and moves the look over the ground: the
    plugin gives the corners (aoe drag), the villager in the box is selected, and no block breaks. A short click on
    the ground is a click (score 1)."""
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(5)                                                  # the world is drawn
        game.forceload()
        g = gather.Gather(game, data).setup()
        v = next(iter(g.villagers.values()))
        for c in ("forceload add 0 0", "fill -8 99 -2 8 99 12 stone", "fill -8 100 -2 8 104 12 air",
                  f"tp {v.uuid} -1.5 100 4.5", "gamemode creative aoe2mc",
                  "item replace entity aoe2mc hotbar.0 with "
                  "minecraft:carrot_on_a_stick[tool={rules:[],can_destroy_blocks_in_creative:false}]"):
            game.command(c)
        v.pos = (-1.5, 100.0, 4.5)
        client.key("1")
        game.command("tp aoe2mc 0.5 100 0.5 40 20")                    # looks at the ground south-west
        time.sleep(3)
        client.xdo("mousedown", 1)
        scores = []
        for _ in range(10):
            client.xdo("mousemove_relative", "--", -30, 0)             # the look turns to the south-east
            scores.append(game.command("scoreboard players get aoe2mc aoe_left"))
            time.sleep(0.1)
        time.sleep(0.5)
        client.shot(str(tmp_path / "drag.png"))
        client.xdo("mouseup", 1)
        time.sleep(1)
        assert all("none is set" in c for c in scores), scores             # one drag, no click while the button is down
        assert "has 2" in game.command("scoreboard players get aoe2mc aoe_left")
        g.clicks()
        assert g.selected == {v.uuid}
        assert "passed" in game.command("execute if block 0 99 1 minecraft:stone")   # no broken block
        game.command("tp aoe2mc 0.5 100 0.5 0 60")
        time.sleep(1.5)
        client.xdo("click", 1)                                         # a short click on the ground: deselect
        time.sleep(1.5)
        g.clicks()
        assert g.selected == set()
        game.command("scoreboard players set aoe2mc aoe_build 1")     # a chosen building: a placement at once
        client.xdo("click", 1)
        time.sleep(0.3)                                                # less than Drag.FIRST (1 s)
        assert "has 1" in game.command("scoreboard players get aoe2mc aoe_left")
