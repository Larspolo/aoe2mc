"""The garrison bonuses of the civilizations (#2117, AoE2 DE wiki, civs.GARRISON): Khmer villagers garrison in houses,
Teuton towers and town centers take more units."""
from test_garrison_game import Server, arrive
from test_gather import grid

from game import civs, combat, garrison, gather

HOUSE = (16, 18, 2, 4)


def setup(civ, villagers=6):
    """A flat 24 × 24 map: an own town center, watch tower and house, villagers and one man-at-arms south of them."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "WATCH_TOWER", "player": 1, "tile": [11.0, 3.0], "footprint": [10, 2, 12, 4]},
               {"kind": "building", "name": "HOUSE", "player": 1, "tile": [17.0, 3.0], "footprint": [16, 2, 18, 4]}]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [6.5 + k, 9.5]}
                for k in range(villagers)]
    objects += [{"kind": "unit", "name": "MAN_AT_ARMS", "player": 1, "uuid": "m", "tile": [6.5, 12.5]}]
    server = Server({f"v{k}": {"Pos": (6.5 + k, 64.0, 9.5)} for k in range(villagers)} |
                    {"m": {"Pos": (6.5, 64.0, 12.5)}, "Steve": {"Pos": (3.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.paper = True
    server.targets = {combat.target_uuid(o["footprint"]) for o in objects if o["kind"] == "building"}
    return server, g


def test_the_sizes_of_the_civilizations():
    _, g = setup("KHMER")
    assert garrison.size(g, "HOUSE") == civs.GARRISON["KHMER"]["HOUSE"] > 0
    assert garrison.size(g, "TOWN_CENTER") == garrison.SIZES["TOWN_CENTER"]           # no bonus: the normal size
    _, g = setup("TEUTONS")
    assert garrison.size(g, "HOUSE") == 0
    assert all(garrison.size(g, t) == n > garrison.SIZES[t] for t, n in civs.GARRISON["TEUTONS"].items())
    _, g = setup("BRITONS")
    assert garrison.size(g, "HOUSE") == 0 and garrison.size(g, "WATCH_TOWER") == garrison.SIZES["WATCH_TOWER"]


def test_a_khmer_house_takes_its_size_of_villagers_and_no_soldier():
    n = civs.GARRISON["KHMER"]["HOUSE"]
    server, g = setup("KHMER", villagers=n + 1)
    assert HOUSE in garrison.holders(g)
    g.choose({f"v{k}" for k in range(n + 1)} | {"m"}, "v0")
    assert garrison.order(g, "Steve", (16, 2)) == HOUSE
    assert "m" not in g.entering and len(g.entering) == n + 1            # the man-at-arms does not go
    arrive(server, g, HOUSE)
    assert len(g.garrisons[HOUSE]) == n                                  # the last villager stays at the door
    assert any(c.endswith(" 0") and c.startswith("aoe arrows") for c in server.log)   # a house does not shoot
    g.choose({"m"}, "m")
    assert garrison.order(g, "Steve", (16, 2)) is None                  # a soldier alone: no garrison order


def test_a_house_of_another_civilization_takes_no_garrison():
    server, g = setup("BRITONS")
    assert HOUSE not in garrison.holders(g)
    g.choose({"v0"}, "v0")
    assert garrison.order(g, "Steve", (16, 2)) is None


def test_a_teuton_watch_tower_takes_more_units():
    n = civs.GARRISON["TEUTONS"]["WATCH_TOWER"]
    server, g = setup("TEUTONS", villagers=n + 1)
    tower = (10, 12, 2, 4)
    g.choose({f"v{k}" for k in range(n + 1)}, "v0")
    assert garrison.order(g, "Steve", (10, 2)) == tower
    arrive(server, g, tower)
    assert len(g.garrisons[tower]) == n > garrison.SIZES["WATCH_TOWER"]
