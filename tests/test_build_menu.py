"""game/build.py: a right click on a selected villager opens the build menu, a chest menu (#621). Fake server."""
import re
import shutil
import sys
from urllib.parse import unquote

import pytest

from test_build_site import Server
from test_gather import grid

from game import build, gather

sys.path.insert(0, "tools")


class MenuServer(Server):
    """The fake server of test_build_site, where "scoreboard players set" sets the /trigger choice."""

    def command(self, cmd):
        if m := re.fullmatch(r"scoreboard players set Steve aoe_build (\d+)", cmd):
            self.chosen = int(m[1])
        return super().command(cmd)


def villager_map():
    """A flat 24 × 24 map with a villager at block (10.5, 12.5). Steve stands west of it and looks at it."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [10.5, 12.5]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = MenuServer({"v": {"Pos": (10.5, 64.0, 12.5)}, "Steve": {"Pos": (8.5, 64.0, 12.5), "Rotation": (-90.0, 20.0)}})
    g = gather.Gather(server, data).setup()
    g.stock["wood"] = 200
    return server, g


def test_the_menu_has_one_item_per_building_with_cost_and_time():
    items = build.items()
    assert [unquote(name) for _, _, name, _ in items] == [build.pretty(n) for n in build.MENU]
    assert [s for s, *_ in items] == list(range(len(build.MENU)))
    assert items[0] == (0, "spruce_stairs", "House", "25 wood\n25 s")
    assert items[build.MENU.index("TOWN_CENTER")][3] == "275 wood, 100 stone\n150 s"


def test_each_icon_is_a_block_of_the_design():
    import render
    for name, icon in build.ICONS.items():
        states = render.building_blocks(name, "western")[3]
        assert icon in {s.removeprefix("minecraft:").split("[")[0] for s in states}, name


def test_a_click_on_a_selected_villager_opens_the_menu_and_a_choice_closes_it():
    server, g = villager_map()
    g.click("Steve")                                                   # the first click selects the villager
    assert g.selected == {"v"} and not g.menus
    g.click("Steve")                                                   # the second click opens the build menu
    assert "Steve" in g.menus
    cmds = [c for c in server.log if c.startswith(("aoe menu Steve Build ", "aoe menu-add Steve Build "))]
    specs = [x for c in cmds for x in c.split(" ")[4:]]                 # more commands below the RCON limit (#1647)
    last = build.SHELTER                                               # the last slot: Seek Shelter (#3440)
    assert cmds[0].startswith(f"aoe menu Steve Build {last}:") and all(len(c) <= 1446 for c in cmds)
    assert "0:spruce_stairs:House:25%20wood%0A25%20s" in specs and len(specs) == 2 + sum(not build.hidden(g, n) for n in build.MENU)
    g.menus["Steve"]("Steve", 0, False)                                # the player clicks the house
    assert server.chosen == 1 and build.chosen(g, "Steve") == "HOUSE"
    assert "aoe menu-close Steve" in server.log and not g.menus


def test_after_the_choice_the_next_click_on_the_ground_places_the_building():
    server, g = villager_map()
    g.select("v")
    build.open_menu(g, "Steve")
    g.menus["Steve"]("Steve", 0, False)
    server.entities["Steve"]["Rotation"] = (180.0, 30.0)              # look north, at the ground
    g.click("Steve")
    site, = g.sites
    assert site["name"] == "HOUSE" and g.stock["wood"] == 175 and server.chosen == 0


def test_a_click_on_an_empty_slot_chooses_nothing():
    server, g = villager_map()
    build.open_menu(g, "Steve")
    g.menus["Steve"]("Steve", 53, False)
    assert server.chosen == 0 and "Steve" in g.menus


@pytest.mark.mc
def test_the_build_menu_is_valid_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import menu, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        answers = [game.command(c).strip() for c in menu.commands("@a", "Build", build.items())]   # in parts (#2556)
        assert answers == ["Menu: 0 players"] * len(answers)          # no "Bad item"
