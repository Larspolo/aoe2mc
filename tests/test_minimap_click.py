"""game/map_table.py: a right click with the command stick on a pixel of the framed map of the map table sends the
selection to the block of that pixel, as a right click on the AoE2 minimap (#2586, owner decision #2585: option A).
The plugin (MapTable.java) sets the block of the pixel in the scores aoe_map_x and aoe_map_z, then aoe_map."""
import json
import math
import re
import shutil

import pytest
from test_gather import FakeServer, grid
from test_move_order import moves

from game import gather, map_table

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [8, 8, 12, 12]}


def setup():
    """A flat 64 × 64 map (tile size 1) with a town center of player 1 and an own militia "m0"."""
    objects = [TC, {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m0", "tile": [4.5, 30.5]}]
    server = FakeServer({"m0": {"Pos": (4.5, 64.0, 30.5)}})
    g = gather.Gather(server, grid([[64] * 64 for _ in range(64)], objects)).setup()
    g.paper = True
    map_table.setup(g)
    return server, g


def block(p, center, scale):
    """The block in the middle of map pixel p (MapTable.block): pixel 0 starts at center - 64 × 2^scale."""
    return center - 64 * (1 << scale) + p * (1 << scale) + (1 << scale) // 2


def click(server, x, z):
    server.scores.update({map_table.CLICK: 1, map_table.X: x, map_table.Z: z})


def test_the_table_stands_at_the_south_east_corner_of_the_town_center_with_map_0():
    server, g = setup()
    assert "setblock 12 64 12 minecraft:cartography_table" in server.log
    frame = next(c for c in server.log if c.startswith("summon minecraft:glow_item_frame 12 65 12 "))
    item = json.loads(re.search(r"Item:(\{.*\})\}$", frame)[1])
    assert item["components"] == {"minecraft:map_id": 0} and "Facing:1b" in frame and "Fixed:1b" in frame
    assert (12, 12) in g.map.blocked                                   # no unit walks into the table


def test_a_click_on_pixel_p_q_sends_the_selection_to_the_block_of_that_pixel():
    server, g = setup()
    g.choose({"m0"}, "m0")
    server.log.clear()
    x, z = block(40, 64, 0), block(20, 64, 0)                          # a world of 64 blocks: scale 0, center 64
    click(server, x, z)
    map_table.tick(g)
    assert moves(server) == {"m0": (x + 0.5, z + 0.5)} == {"m0": (40.5, 20.5)}
    assert map_table.CLICK not in server.scores                       # one order per click


def test_a_click_with_no_selection_gives_no_order():
    server, g = setup()
    server.log.clear()
    click(server, 40, 20)
    map_table.tick(g)
    assert not moves(server) and map_table.CLICK not in server.scores


def test_no_order_on_vanilla():
    server, g = setup()
    g.paper = False
    server.log.clear()
    click(server, 40, 20)
    map_table.tick(g)
    assert server.log == []


@pytest.mark.mc
def test_a_click_on_the_framed_map_sends_a_villager_on_paper(tiny_world, tmp_path):
    """A real client on Paper right clicks with the command stick on a pixel of the framed map 0: the plugin sets the
    block of that pixel (the reverse of `aoe minimap pixel`), and the selected villager walks there."""
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
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
        assert g.paper and "passed" in game.command(f"execute if entity @e[tag={map_table.TAG}.p1]")
        v = next(iter(g.villagers.values()))
        item = '{id:"minecraft:filled_map",count:1,components:{"minecraft:map_id":0}}'
        for c in ("forceload add 0 0", "fill -2 99 -2 2 99 2 stone", "fill -2 100 -2 2 103 2 air",
                  f"summon minecraft:glow_item_frame 0 100 0 {{Facing:1b,Fixed:1b,Item:{item}}}",
                  "item replace entity aoe2mc hotbar.0 with minecraft:carrot_on_a_stick"):
            game.command(c)
        client.key("1")
        game.command("tp aoe2mc 0.27 100 0.77 0 90")                   # looks down at x = -0.23, z = +0.27 of the frame
        time.sleep(2)
        client.shot(str(tmp_path / "table.png"))
        g.choose({v.uuid}, v.uuid)
        client.xdo("click", "3")
        time.sleep(1.5)
        x, z = map_table.score(g, "aoe2mc", map_table.X), map_table.score(g, "aoe2mc", map_table.Z)
        assert game.command(f"aoe minimap pixel {x} {z}").strip().endswith(" 34 98")
        g.clicks()
        assert v.state == "to_rally" and math.dist(v.goal, (x, z)) <= 2
