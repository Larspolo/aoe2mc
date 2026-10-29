"""game/build.py: a player places a construction site with the command stick (#417). Fake server, no Minecraft."""
import re

from test_gather import FakeServer, grid

from game import build, gather


class Server(FakeServer):
    """The fake server of test_gather, with a /trigger score per player."""

    def __init__(self, entities, chosen=0):
        super().__init__(entities)
        self.chosen = chosen

    def command(self, cmd):
        if m := re.fullmatch(r"scoreboard players get (\S+) aoe_build", cmd):
            self.log.append(cmd)
            return f"{m[1]} has {self.chosen} [aoe_build]" if self.chosen else f"Can't get value of aoe_build for {m[1]}"
        if re.fullmatch(r"scoreboard players set \S+ aoe_build 0", cmd):
            self.chosen = 0
        return super().command(cmd)


def site_map(wood=200, chosen=1):
    """A flat 24 × 24 map (tile size 1): a town center at blocks 2..4, a tree at tile (12, 12), water at x = 20."""
    rows = [[64] * 24 for _ in range(24)]
    for z in range(24):
        rows[z][20] = "-"
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "other", "name": "TREE_OAK", "tile": [12.5, 12.5]}]
    data = grid(rows, objects)
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = Server({"Steve": {"Pos": (8.5, 64.0, 12.5), "Rotation": (-90.0, 30.0)}}, chosen)
    g = gather.Gather(server, data).setup()
    g.stock["wood"] = wood
    return server, g


def test_new_players_get_the_menu_and_the_trigger():
    server, g = site_map()
    assert "scoreboard objectives add aoe_build trigger" in server.log
    g.clicks()
    menu = next(c for c in server.log if c.startswith("execute as @a unless score @s aoe_build matches 0.. run tellraw @s "))
    assert "/trigger aoe_build set 1: House (" in menu and "Town Center (" in menu
    assert "scoreboard players enable @a aoe_build" in server.log


def test_a_click_places_a_foundation_and_takes_the_cost():
    server, g = site_map()
    eye, d = (8.5, 65.62, 12.5), gather.direction(-90, 30)           # look east and down
    cell = g.map.pick_ground(eye, d)
    assert cell[1] == 12 and 9 < cell[0] < 12
    g.click("Steve")
    site, = g.sites
    x0, x1, z0, z1 = site["footprint"]
    assert site["name"] == "HOUSE" and x1 - x0 == z1 - z0 == 2 and x0 <= cell[0] < x1 and z0 <= cell[1] < z1
    wood = build.price(g, "HOUSE")["wood"]
    assert g.stock["wood"] == 200 - wood and f"scoreboard players remove Wood aoe_res {wood}" in server.log
    wool = [c for c in server.log if c.startswith("setblock ")]
    assert len(wool) == 4 and all(c.endswith(" 64 " + c.split()[3] + " minecraft:blue_wool") for c in wool)
    assert not any(g.map.free(x, z) for x in range(x0, x1) for z in range(z0, z1))
    assert server.chosen == 0
    assert g.map.path((8, 8), {(x0 + 3, z0)}) and not set(g.map.path((8, 8), {(x0 + 3, z0)})) & {(x0, z0)}


def test_no_foundation_without_space_or_resources():
    server, g = site_map(wood=20)
    g.click("Steve")
    assert not g.sites and g.stock["wood"] == 20 and any("Not enough resources" in c for c in server.log)
    server, g = site_map()
    assert not build.free(g, build.area(g, "HOUSE", (12, 12)))      # the tree
    assert not build.free(g, build.area(g, "HOUSE", (3, 3)))        # the town center
    assert not build.free(g, build.area(g, "HOUSE", (20, 8)))       # water
    assert not build.free(g, build.area(g, "TOWN_CENTER", (0, 15)))  # outside the map
    assert build.free(g, build.area(g, "TOWN_CENTER", (8, 18)))
    server.entities["Steve"]["Rotation"] = (90.0, 30.0)              # look west, at the town center area
    server.entities["Steve"]["Pos"] = (7.5, 64.0, 3.5)
    g.click("Steve")
    assert not g.sites and any("No space" in c for c in server.log)


def test_without_a_choice_a_click_does_what_it_did():
    server, g = site_map(chosen=0)
    g.click("Steve")
    assert not g.sites and not any(c.startswith("setblock ") for c in server.log)
