"""game: a Khitan player builds the Pasture in place of the Farm (#4118): a farm in a fenced building with
PASTURE["food"] food for at most two herders, who drop the food at the Pasture."""
from test_build_site import Server
from test_folwark import DOWN, complete
from test_gather import grid

from game import build, gather


def khitan(civ="KHITANS", villagers=("v0",)):
    """A flat 96 × 96 block map (tile size 4), a town center and villagers of player 1 of civ."""
    data = grid([[64] * 96 for _ in range(96)], [])
    data["objects"].append({"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5],
                            "footprint": [4, 4, 20, 20]})
    data["objects"] += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": u} for u in villagers]
    data.update(tile_size=4, level_height=1, players={"1": {"civ": civ, "color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN},
                     **{u: {"Pos": (60.5, 64.0, 30.5 + 2 * i)} for i, u in enumerate(villagers)}})
    g = gather.Gather(server, data, carry=10, chop=0.25).setup()
    g.stock.update(wood=1000)
    return server, g


def pasture(g):
    site = complete(g, "PASTURE", 60, 60)
    return site, (site["footprint"][0] // 4 + 1, site["footprint"][2] // 4 + 1)


def test_the_khitans_build_a_pasture_and_no_farm():
    _, g = khitan()
    assert not build.hidden(g, "PASTURE") and build.hidden(g, "FARM")
    _, g = khitan("BRITONS")
    assert build.hidden(g, "PASTURE") and not build.hidden(g, "FARM")


def test_a_pasture_takes_two_herders_and_a_third_gets_no_place():
    _, g = khitan(villagers=("a", "b", "c"))
    _, tile = pasture(g)
    g.selected = {"a", "b", "c"}
    g.send(tile)
    assert [g.villagers[u].tree for u in "abc"] == [tile, tile, None]
    assert g.villagers["c"].state == "idle" and g.tended(tile)


def test_a_pasture_gives_its_food_and_the_herders_drop_it_at_the_pasture():
    server, g = khitan(villagers=("a", "b"))
    site, tile = pasture(g)
    assert g.map.farms[tile] == gather.PASTURE["food"]
    g.selected = {"a", "b"}
    g.send(tile)
    food = g.stock["food"]
    x0, x1, z0, z1 = site["footprint"]
    assert g.drop_goals(g.villagers["a"]) == g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
    for _ in range(40000):
        g.step()
        if tile not in g.map.farms and all(v.load == 0 for v in g.villagers.values()):
            break
    assert g.stock["food"] - food == gather.PASTURE["food"]
