"""game/build.py, game/gather.py: the mule cart of the Armenians and Georgians (#2194, AoE2 DE wiki "Mule Cart"). It is
the drop site of wood, gold, stone and hunted meat, in place of the lumber camp and the mining camp, and counts for the
Feudal Age. Fake server, no Minecraft."""
import re

from test_build_done import DOWN
from test_build_site import Server as SiteServer
from test_gather import grid

import buildings
import units
from game import build, civs, gather, train

HAVE = sorted(set(buildings.CIV_TO_ARCH) - set(civs.MISSING["MULE_CART"]))   # the Armenians and Georgians


class Server(SiteServer):
    """The fake server of test_build_site that keeps the summoned mobs, and an "aoe moveto" puts a mob at its goal."""

    def command(self, cmd):
        if m := re.fullmatch(r"summon \S+ (\S+) (\S+) (\S+) .*UUID: ?\[I; ?([-\d, ]+)\].*", cmd):
            self.entities[units.uuid_str(m[4].split(","))] = {"Pos": tuple(map(float, m.groups()[:3]))}
        if (m := re.fullmatch(r"aoe moveto (\S+) (\S+) (\S+) (\S+)", cmd)) and m[1] in self.entities:
            self.entities[m[1]]["Pos"] = tuple(map(float, m.groups()[1:]))
        return super().command(cmd)


def setup(civ, objects=()):
    """A flat 48 × 48 block map of a player of civ with one idle villager v0, the mule cart chosen."""
    data = grid([[64] * 48 for _ in range(48)], objects)
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western", "civ": civ}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}},
                    chosen=build.MENU.index("MULE_CART") + 1)
    g = gather.Gather(server, data, carry=5, chop=0.25).setup()
    g.stock.update(food=500, wood=500)
    return server, g


def left(g, res):
    """The stock of res after the cost of the mule cart."""
    return 500 - build.price(g, "MULE_CART").get(res, 0)


def done(objects=(), civ=HAVE[-1]):
    """A villager of civ (the Georgians) builds a mule cart at blocks 4.."""
    server, g = setup(civ, objects)
    g.click("Steve")
    site, = g.sites
    assert site["name"] == "MULE_CART" and g.stock == {**g.stock, "food": left(g, "food"), "wood": left(g, "wood")}
    g.select("v0")
    g.click("Steve")
    for _ in range(3000):
        g.step()
        if site["progress"] == 1:
            break
    assert site["progress"] == 1
    x0, x1, z0, z1 = site["footprint"]
    return server, g, {(x, z) for x in range(x0, x1) for z in range(z0, z1)}


def test_it_takes_wood_gold_stone_and_meat():
    server, g, cells = done()
    assert {r for r, sites in g.map.drops.items() if cells in sites} == {"wood", "gold", "stone", "meat"}


def test_villagers_carry_wood_to_it():
    server, g, cells = done([{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 1.5]}])
    g.send((5, 1))
    v = g.villagers["v0"]
    for _ in range(400):
        g.step()
        if v.state == "to_drop" and not v.path:
            assert v.cell in g.map.around(cells)
    assert server.wood() >= 10 and g.stock["wood"] == left(g, "wood") + server.wood()


def test_a_hunter_carries_meat_to_it():
    server, g, cells = done()
    assert cells in g.map.drops["meat"] and cells not in g.map.drops["food"]   # no berries, no farm food
    v = g.villagers["v0"]
    g.map.carcasses[(5, 1)] = 100
    v.res, v.tree, v.load, v.state = "food", (5, 1), g.limit("food") - 1, "chop"
    seen = set()
    for _ in range(400):
        g.step()
        seen.add(v.state)
        if g.stock["food"] > left(g, "food"):
            break
    assert "to_drop" in seen and g.stock["food"] == left(g, "food") + g.limit("food") and v.cell in g.map.around(cells)


def test_the_franks_cannot_build_it():
    server, g = setup(min(civs.MISSING["MULE_CART"]))
    assert build.chosen(g, "Steve") is None and civs.missing(g, "MULE_CART")
    g.click("Steve")
    assert not g.sites and g.stock["wood"] == 500


def test_armenians_and_georgians_have_no_lumber_or_mining_camp():
    have = set().union(*civs.MISSING.values()) - set(civs.MISSING["MULE_CART"])
    assert have and have <= set(civs.MISSING["LUMBER_CAMP"]) & set(civs.MISSING["MINING_CAMP"])


def test_it_counts_for_the_feudal_age():
    barracks = {"kind": "building", "name": "BARRACKS", "player": 1, "tile": [10, 10], "footprint": [36, 36, 44, 44]}
    server, g = setup(HAVE[0], [barracks])
    assert train.missing(g, "FEUDAL_AGE").endswith("(1/2)")
    server, g, cells = done([barracks], HAVE[0])
    assert train.missing(g, "FEUDAL_AGE") is None
