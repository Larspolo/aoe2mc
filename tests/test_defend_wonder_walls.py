"""#2462: in the game mode "Defend the Wonder" each attacker starts with a complete Castle, and the base of each player
has a closed ring of Stone Walls with a gate (AoE2 wiki "Defend the Wonder", as the map Arena). Fake server of
test_gather, a map with the town centers of two players."""
from test_gather import FakeServer, grid

from game import bot, defend_wonder, gather

MODE = defend_wonder.MODE
RING = MODE["ring"]
TCS = {1: [22, 22, 26, 26], 2: [70, 22, 74, 26]}                       # [x0, z0, x1, z1], tile size 1


def game(teams=(1, 2)):
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": p, "footprint": f} for p, f in TCS.items()]
    data = grid([[64] * 96 for _ in range(96)], objects)
    data.update(level_height=1, players={"1": {"color": "blue", "arch": "western", "team": teams[0]},
                                         "2": {"color": "red", "arch": "western", "team": teams[1]}})
    server = FakeServer({})
    g = gather.Gather(server, data, carry=10, chop=0.05, start={}).setup()
    g.bots = [bot.Bot(server, data, player=2, share=g).setup()]
    g.mode = "defend-the-wonder"
    return defend_wonder.setup(g)


def players(g):
    return {1: g, 2: g.bots[0].g}


def test_each_attacker_starts_with_a_complete_castle():
    g = game()
    castles = {n: [s for s in h.sites if s["name"] == "CASTLE"] for n, h in players(g).items()}
    count = lambda side: MODE["side_buildings"].get(side, {}).get("CASTLE", 0)   # noqa: E731
    assert {n: len(c) for n, c in castles.items()} == {1: count("defender"), 2: count("attacker")}   # player 1 defends
    assert all(s["done"] for c in castles.values() for s in c)
    assert len([s for s in game(teams=(1, 1)).bots[0].g.sites if s["name"] == "CASTLE"]) == count("ally")


def inside(h, start):
    """The free cells that a unit reaches from the block cell start (4 neighbours)."""
    seen, todo = {start}, [start]
    while todo:
        x, z = todo.pop()
        for c in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if c not in seen and h.map.free(*c):
                seen.add(c)
                todo.append(c)
    return seen


def test_the_base_of_the_defender_is_inside_a_closed_ring_of_stone_walls_with_a_gate():
    g = game()
    r, (x0, z0, x1, z1) = RING["radius"], TCS[1]
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    walls = [s for s in g.sites if s["name"] == RING["wall"]]
    gates = [s for s in g.sites if s["name"] == RING["gate"]]
    assert len(gates) == 1 and all(s["done"] for s in walls + gates) and len(walls) == 8 * r - 4
    reach = inside(g, (cx, z1))                                        # south of the town center
    assert reach and all(max(abs(x - cx), abs(z - cz)) < r for x, z in reach)   # closed: no way out
    wonder = next(s for s in g.sites if s["name"] == "WONDER")
    wx0, wx1, wz0, wz1 = wonder["footprint"]
    assert max(abs(wx0 - cx), abs(wx1 - 1 - cx), abs(wz0 - cz), abs(wz1 - 1 - cz)) < r   # the Wonder is inside
    gx0, gx1, gz0, gz1 = gates[0]["footprint"]
    assert (gx1 - gx0, gz1 - gz0) == (4, 1) and gz0 == cz + r          # 4 tiles on the south side
    assert any(s["name"] == RING["wall"] for s in g.bots[0].g.sites)  # the attacker has a ring too


def test_a_loaded_game_gets_no_second_ring():
    g = game()
    n = len(g.sites)
    defend_wonder.setup(g, start=False)
    assert len(g.sites) == n
