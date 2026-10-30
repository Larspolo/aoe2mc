"""The "Go to" compass menu of the game program (#1830): its items and the view command of each kind of place."""
from urllib.parse import unquote

import pytest
from test_loom import setup

from game import gather, goto


def menu(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu Steve")][-1]


def views(server):
    return [c for c in server.log if c.startswith("aoe view ")]


def test_the_item_goes_to_slot_2_with_the_other_items():
    server, g = setup()
    g.calls = 0
    g.clicks()
    assert any("hotbar.2 with minecraft:carrot_on_a_stick[item_model=\"minecraft:compass\",item_name=\"Go to\"" in c
               for c in server.log)
    assert goto.SLOT not in (s for s, _ in gather.GROUPS.values()) and goto.SLOT != gather.diplomacy.SLOT


def test_the_menu_has_the_town_center_the_groups_and_the_idle_villager():
    server, g = setup()
    g.groups[1] = {"m"}
    goto.open_menu(g, "Steve")
    text = menu(server)
    assert "0:bell:Town center 1:Go to this town center." in text
    assert "9:red_dye:Group 1: 1 units:" in text
    assert "10:gray_dye:Group 2: 0 units:" in text                    # an empty group is gray
    idle = [v for v in g.villagers.values() if v.state == "idle"]
    assert f"18:{'wooden_hoe' if idle else 'gray_dye'}:Idle villager:" in text


def test_a_click_on_the_town_center_goes_above_its_center():
    server, g = setup()
    goto.open_menu(g, "Steve")
    assert goto.button(g, "Steve", 0) == (3.5, 3.5)                    # footprint x 2-4, z 2-4
    assert views(server) == ["aoe view Steve 3.5 3.5"]
    assert "aoe menu-close Steve" in server.log and "Steve" not in g.menus


def test_a_click_on_a_group_selects_it_and_goes_to_its_unit():
    server, g = setup()
    g.groups[1] = {"m"}
    assert goto.button(g, "Steve", goto.GROUP_ROW) == (9.5, 9.5)
    assert g.selected == {"m"} and views(server) == ["aoe view Steve 9.5 9.5"]


def test_a_gray_item_does_nothing():
    server, g = setup()
    g.data["objects"] = [o for o in g.data["objects"] if o["kind"] != "building"]
    assert goto.button(g, "Steve", 0) is None                          # no town center
    assert goto.button(g, "Steve", goto.GROUP_ROW + 1) is None         # an empty group
    for v in g.villagers.values():
        v.state = "work"
    assert goto.button(g, "Steve", goto.IDLE) is None
    assert views(server) == []


def test_idle_villager_goes_to_the_next_one_at_each_click():
    server, g = setup()
    first = next(iter(g.villagers.values()))
    second = gather.Villager("w", (12.5, 64.0, 3.5))
    g.villagers["w"] = second
    first.state = second.state = "idle"
    assert goto.button(g, "Steve", goto.IDLE) == (7.5, 7.5) and g.selected == {"v"}
    assert goto.button(g, "Steve", goto.IDLE) == (12.5, 3.5) and g.selected == {"w"}
    assert goto.button(g, "Steve", goto.IDLE) == (7.5, 7.5)            # then the first one again


@pytest.mark.mc
def test_a_player_opens_the_menu_and_goes_to_the_town_center(tiny_world, tmp_path):
    import json
    import os
    import re
    import shutil
    import time

    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.forceload()
        g = gather.Gather(game, data).setup()
        (x, z), = goto.centers(g)[:1] or pytest.skip("no town center of player 1 in the tiny world")
        game.command("tp aoe2mc 2 120 2")
        end = time.time() + 20
        while not goto.in_hand(g, "aoe2mc") and "passed" not in game.command(
                "execute if items entity aoe2mc hotbar.2 *[custom_data={aoe_goto:1b}]"):   # data get cuts the text
            assert time.time() < end, "no Go to item"
            g.clicks()
            time.sleep(0.5)
        for _ in range(9):                                             # the wheel to hotbar slot 2: no focus for keys
            if goto.in_hand(g, "aoe2mc"):
                break
            client.xdo("click", "5")
            time.sleep(0.6)
        assert goto.in_hand(g, "aoe2mc")
        client.shot(str(tmp_path / "hand.png"))
        client.xdo("click", "3")                                       # a right click with the compass
        end = time.time() + 10
        while "aoe2mc" not in g.menus:
            assert time.time() < end, "the menu did not open"
            g.clicks()
            time.sleep(0.3)
        time.sleep(1)
        client.shot(str(tmp_path / "menu.png"))
        client.click(*client.slot(0, 3))                               # "Town center 1"
        time.sleep(1)
        menu_clicks = g.clicks()
        time.sleep(2)
        client.shot(str(tmp_path / "view.png"))
        pos = [float(v) for v in re.findall(r"(-?[\d.]+)d", game.command("data get entity aoe2mc Pos"))]
    assert "aoe2mc" not in g.menus, menu_clicks                         # the click closed the menu
    assert abs(pos[0] - x) < 1 and abs(pos[2] - (z + 12)) < 1, (pos, x, z)
