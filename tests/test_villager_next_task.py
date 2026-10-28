"""A villager works on after it builds a farm or a camp, or after its tree is gone, as in AoE2 (#3271). Fake server."""
from test_build_site import Server
from test_gather import grid

from game import build, gather


def town(objects=(), villagers=2):
    """A flat 40 × 40 map (tile size 1) with the objects and villagers near the block (20, 20)."""
    data = grid([[64] * 40 for _ in range(40)], objects)
    data.update(level_height=1, players={"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}})
    ents = {"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": (0.0, 90.0)}}
    for i in range(villagers):
        data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{i}"})
        ents[f"v{i}"] = {"Pos": (20.5 + i, 64.0, 20.5)}
    g = gather.Gather(Server(ents, chosen=1), data, start={}).setup()
    g.stock.update(wood=500, stone=500)
    return g


def built(g, name, rect):
    """Found a site of name, send all villagers to build it and step until it is complete."""
    site = build.found(g, name, rect)
    g.build(site, set(g.villagers))
    for _ in range(3000):
        g.step()
        if site.get("done"):
            break
    assert site.get("done")
    return site


def test_a_builder_farms_the_new_farm():
    g = town()
    built(g, "FARM", (14, 17, 14, 17))
    tile = g.map.farm_at[(14, 14)]
    farmer = g.villagers[g.farmers[tile]]
    assert farmer.state == "to_tree" and farmer.tree == tile
    assert sum(v.state == "idle" for v in g.villagers.values()) == 1    # one farmer on a farm, the other stops


def test_the_builders_mine_after_a_mining_camp():
    g = town([{"kind": "other", "name": "GOLD_MINE", "tile": [30.5, 30.5]},
              {"kind": "other", "name": "STONE_MINE", "tile": [5.5, 5.5]}])
    built(g, "MINING_CAMP", (26, 28, 26, 28))
    assert {(v.state, v.tree, v.res) for v in g.villagers.values()} == {("to_tree", (30, 30), "gold")}


def test_a_lumberjack_goes_to_the_next_tree():
    g = town([{"kind": "other", "name": "TREE_OAK", "tile": [25.5, 20.5]},
              {"kind": "other", "name": "TREE_OAK", "tile": [28.5, 20.5]},
              {"kind": "building", "name": "LUMBER_CAMP", "player": 1, "tile": [24, 25], "footprint": [23, 23, 25, 27]}],
             villagers=1)
    v = g.villagers["v0"]
    g.send((25, 20), {"v0"})
    g.map.trees[(25, 20)] = 1                                          # one wood left
    for _ in range(3000):
        g.step()
        if v.tree == (28, 20):
            break
    assert v.tree == (28, 20) and v.state == "to_tree"


def test_a_builder_of_a_house_stays_idle():
    g = town(villagers=1)
    built(g, "HOUSE", (14, 16, 14, 16))
    assert g.villagers["v0"].state == "idle"
