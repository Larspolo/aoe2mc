"""game/train.py: the university researches Fortified Wall in the Castle Age (#1326). The new and the complete own stone
walls get the fortified wall design and its values (combat.wall); a gate becomes a fortified gate. A damaged wall or
gate keeps its lost hit points."""
import math

from test_gather import grid
from test_loom import menus
from test_repair import HpServer

from game import build, combat, gather, train

UNI = (8, 12, 8, 12)                                               # block footprint (x0, x1, z0, z1), tile size 1
COST, SLOT = train.COSTS["FORTIFIED_WALL"], train.ITEMS["FORTIFIED_WALL"][0]
WALL, FORT = combat.wall("STONE_WALL", 2), combat.wall("FORTIFIED_WALL", 2)          # the Castle Age values
GATE, FORT_GATE = combat.wall("GATE", 2), combat.wall("FORTIFIED_GATE", 2)


def entry(g, name, state):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def setup(age=2):
    """A flat 24 × 24 map with an own town center and university, the first `age` ages, and the stock for the
    research, 4 tiles of stone wall and a gate."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "UNIVERSITY", "player": 1, "tile": [10, 10], "footprint": [8, 8, 12, 12]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}, 1
    server = HpServer({}, {})
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS[:age])
    g.stock.update({"stone": 50} | COST)
    return server, g


def walls(server, g, z, n):
    """A complete line of n stone wall tiles at block row z, from x = 14. Returns the UUIDs of their targets."""
    build.wall(g, "Steve", "STONE_WALL", (14, z))
    build.wall(g, "Steve", "STONE_WALL", (14 + n - 1, z))
    out = []
    for s in [s for s in g.sites if s["progress"] < 1]:
        build.rise(g, s, math.inf)
        x0, x1, z0, z1 = s["footprint"]
        out.append(uuid := combat.target_uuid([x0, z0, x1, z1]))
        server.hp[uuid] = 0                                        # the plugin sets the full hit points
    return out


def test_the_university_menu_shows_fortified_wall_from_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        assert train.open_menu(g, "Steve", (9, 9)) == UNI
        assert (":book:Fortified Wall:" in menus(server)[-1]) == shown
    assert entry(g, "FORTIFIED_WALL", "research") in menus(server)[-1]


def test_the_research_gives_the_walls_the_fortified_wall_values_and_a_damaged_wall_keeps_its_loss():
    server, g = setup()
    full, hurt, dead = walls(server, g, 16, 3)
    server.hp[full], server.hp[hurt] = WALL.hp, WALL.hp - 800      # the Castle Age hit points of a stone wall
    del server.hp[dead]                                            # destroyed: the target is gone
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (9, 9)), SLOT) == 1
    assert all(g.stock[r] == 0 for r in COST)
    train.tick(g, train.TRAIN_TIMES["FORTIFIED_WALL"] - 1)
    assert "FORTIFIED_WALL" not in g.techs
    server.log.clear()
    train.tick(g, 1)
    assert "FORTIFIED_WALL" in g.techs
    assert server.hp[full] == FORT.hp and server.hp[hurt] == FORT.hp - 800   # the lost hit points stay lost
    assert any(c.startswith(f"aoe building {full} {FORT.hp} {FORT.melee} {FORT.pierce} ") for c in server.log)
    assert not any(dead in c for c in server.log if "players get" not in c) and not any(c.startswith("summon ") for c in server.log)
    assert f"aoe label {hurt} Fortified Wall" in server.log
    assert any(c.startswith("fill ") or c.startswith("setblock ") for c in server.log)   # the fortified wall design
    assert not train.open_menu(g, "Steve", (9, 9)) or ":Fortified Wall:" not in menus(server)[-1]   # once only


def test_a_new_stone_wall_after_the_research_is_a_fortified_wall():
    server, g = setup()
    g.techs.add("FORTIFIED_WALL")
    assert build.design(g, "STONE_WALL", g.player) == "FORTIFIED_WALL"
    assert build.design(g, "STONE_WALL", g.player + 1) == "STONE_WALL"   # the technology of the own player only
    assert build.design(g, "PALISADE_WALL", g.player) == "PALISADE_WALL"
    uuid, = walls(server, g, 16, 1)
    assert g.sites[0]["name"] == "STONE_WALL"                          # the cost and the build time of a stone wall
    assert any(c.startswith(f"aoe building {uuid} {FORT.hp} {FORT.melee} {FORT.pierce} ") for c in server.log)
    assert f"aoe label {uuid} Fortified Wall" in server.log


def test_the_research_makes_a_complete_gate_a_fortified_gate():
    server, g = setup()
    walls(server, g, 16, 4)
    gate = build.gate(g, "Steve", "GATE", (15, 16))
    build.rise(g, gate, math.inf)
    x0, x1, z0, z1 = gate["footprint"]
    uuid = combat.target_uuid([x0, z0, x1, z1])
    server.hp[uuid] = GATE.hp - 750                                # 750 lost of a Castle Age gate
    train.research(g, {"name": "FORTIFIED_WALL", "player": "Steve"})
    assert server.hp[uuid] == FORT_GATE.hp - 750 and gate["name"] == "GATE"
    assert any(c.startswith(f"aoe building {uuid} {FORT_GATE.hp} {FORT_GATE.melee} {FORT_GATE.pierce} ") for c in server.log)
    assert f"aoe label {uuid} Fortified Gate" in server.log
