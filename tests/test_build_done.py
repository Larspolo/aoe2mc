"""game/build.py: a complete construction site works like a building of the map (#419). Fake server, no Minecraft."""
import pytest
from test_build_site import Server
from test_gather import grid

from game import build, gather

DOWN = (0.0, 90.0)                                                     # yaw, pitch: look straight down


def done(name, objects=()):
    """A complete site of name at blocks 4.. of a flat 48 × 48 block map (tile size 4) and one idle villager v0."""
    data = grid([[64] * 48 for _ in range(48)], objects)
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}},
                    chosen=build.MENU.index(name) + 1)
    g = gather.Gather(server, data, carry=5, chop=0.25).setup()
    g.stock.update(wood=500, stone=500)
    g.click("Steve")
    site, = g.sites
    g.select("v0")
    g.click("Steve")
    for _ in range(3000):
        g.step()
        if site["progress"] == 1:
            break
    assert site["progress"] == 1 and g.villagers["v0"].state in ("idle", "to_tree")   # a camp or farm: work on (#3271)
    x0, x1, z0, z1 = site["footprint"]
    return server, g, {(x, z) for x in range(x0, x1) for z in range(z0, z1)}


@pytest.mark.parametrize("name, res", [("LUMBER_CAMP", {"wood"}), ("MILL", {"food"}),
                                       ("MINING_CAMP", {"gold", "stone"}), ("TOWN_CENTER", set(gather.DROP_SITES))])
def test_a_complete_drop_site_takes_its_resources(name, res):
    server, g, cells = done(name)
    assert {r for r, sites in g.map.drops.items() if cells in sites} == res
    assert not any(g.map.free(*c) for c in cells)


def test_villagers_carry_wood_to_a_new_lumber_camp():
    server, g, cells = done("LUMBER_CAMP", [{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 1.5]}])
    g.send((5, 1))
    v = g.villagers["v0"]
    for _ in range(400):
        g.step()
        if v.state == "to_drop" and not v.path:
            assert v.cell in g.map.around(cells)
    assert server.wood() >= 10 and g.stock["wood"] == 500 - 100 + server.wood()


def test_a_complete_house_is_no_drop_site():
    server, g, cells = done("HOUSE")
    assert not any(g.map.drops.values())


def test_a_complete_farm_can_be_farmed():
    server, g, cells = done("FARM", [{"kind": "building", "name": "MILL", "player": 1, "tile": [9, 1],
                                      "footprint": [32, 0, 40, 8]}])
    tile, = g.map.farms
    assert g.map.farms[tile] == gather.FARM_FOOD and g.map.spot(tile) == cells
    assert all(g.map.free(*c) for c in cells) and g.map.farm_at.keys() == cells
    eye, d = (9.5, 65.62, 9.5), gather.direction(*DOWN)
    assert g.map.pick_tree(eye, d) == tile
    g.click("Steve")                                                   # v0 is still selected: it farms
    v = g.villagers["v0"]
    assert v.tree == tile and g.farmers == {tile: "v0"}
    for _ in range(400):
        g.step()
    assert g.stock["food"] > 0 and g.map.farms[tile] < gather.FARM_FOOD
