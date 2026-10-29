"""#2408: `run.py --play --mode empire-wars` is the AoE2 DE game mode "Empire Wars" (wiki "Empire Wars"): each player
starts with a small town and villagers at work (its line in game/data/setup.jsonl). Fake server of test_gather."""
import collections
import re

from test_gather import FakeServer, grid

from game import build, empire_wars, gather, train

MODE = empire_wars.MODES["empire-wars"]


def town_map():
    """A flat 48 × 48 map (tile size 1): a town center and one villager of player 1, trees in the east, two fruit
    bushes in the south, a gold mine in the west and a stone mine in the north."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [22, 22, 26, 26]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "p1", "tile": [24.5, 27.5]},
               {"kind": "other", "name": "GOLD_MINE", "tile": [12.5, 24.5]},
               {"kind": "other", "name": "STONE_MINE", "tile": [24.5, 12.5]}]
    objects += [{"kind": "other", "name": "TREE_OAK", "tile": [36.5 + x, 20.5 + z]} for x in range(3) for z in range(8)]
    objects += [{"kind": "other", "name": "FRUIT_BUSH", "tile": [23.5 + x, 34.5]} for x in range(2)]
    server = FakeServer({"p1": {"Pos": (24.5, 64.0, 27.5)}})
    command, at = server.command, []

    def track(cmd):                                                    # a new unit gets a position (test_bot_gather)
        if m := re.match(r"summon \S+ (\S+) (\S+) (\S+) ", cmd):
            at[:] = [tuple(map(float, m.groups()))]
        elif (m := re.match(r"aoe stats (\S+) ", cmd)) and at and m[1] not in server.entities:
            server.entities[m[1]] = {"Pos": at[0], "Rotation": (0.0, 0.0)}
        return command(cmd)
    server.command = track
    data = grid([[64] * 48 for _ in range(48)], objects)
    data.update(level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    return gather.Gather(server, data, carry=10, chop=0.05, start={}).setup()


def test_each_player_starts_with_the_town_of_the_mode_for_free():
    g = town_map()
    stock, limit = dict(g.stock), train.limit(g)
    empire_wars.setup(g)
    assert collections.Counter(s["name"] for s in g.sites) == MODE["buildings"]
    assert all(s.get("done") for s in g.sites) and g.stock == stock   # complete and free
    assert train.limit(g) == limit + MODE["buildings"]["HOUSE"] * train.HOUSING["HOUSE"]   # the houses
    camp = next(s for s in g.sites if s["name"] == "MINING_CAMP")["footprint"]
    assert abs((camp[0] + camp[1]) / 2 - 12.5) + abs((camp[2] + camp[3]) / 2 - 24.5) < 8   # next to the gold
    assert len(g.map.own_farms) == MODE["buildings"]["FARM"] and g.map.drops["wood"]


def test_the_villagers_have_a_gather_job_at_the_start():
    g = town_map()
    empire_wars.setup(g)
    n = sum(MODE["villagers"].values())
    assert len(g.villagers) == n and "p1" in g.villagers and g.pop == n
    work = collections.Counter(v.res for v in g.villagers.values() if v.state != "idle")
    assert work == MODE["villagers"]
    assert len(g.farmers) == MODE["buildings"]["FARM"]                 # one farmer on each farm, the others on bushes


def test_a_house_of_a_standard_game_still_costs_wood():
    g = town_map()
    wood = g.stock["wood"]
    site = build.found(g, "HOUSE", build.near(g, "HOUSE", (24, 24)))
    assert g.stock["wood"] == wood - build.COSTS["HOUSE"]["wood"] and not site.get("done")


def test_a_villager_without_a_food_source_chops_wood():
    g = town_map()
    g.map.bushes.clear()                                               # only the farms: the other food villagers chop
    empire_wars.setup(g)
    work = collections.Counter(v.res for v in g.villagers.values() if v.state != "idle")
    v, farms = MODE["villagers"], MODE["buildings"]["FARM"]
    assert work == {"food": farms, "gold": v["gold"], "wood": v["wood"] + v["food"] - farms}
