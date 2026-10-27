"""game/train.py: when the player advances to a new age, the complete own walls and gates get the AoE2 DE hit points
of that age (#1372, wiki infobox: a stone wall 1,080 in the Feudal Age and 1,800 from the Castle Age, a palisade wall
150 and 250 from the Feudal Age). A damaged wall keeps its lost hit points; a destroyed wall stays air."""
import math

from test_fortified_wall import setup, walls

from game import build, combat, train


def advance(g, age):
    train.research(g, {"name": age, "player": "Steve"})


def test_the_castle_age_gives_the_stone_walls_their_castle_age_hit_points():
    server, g = setup(age=1)
    full, hurt, dead = walls(server, g, 16, 3)
    assert any(c.startswith(f"aoe building {full} 1080 8 10 ") for c in server.log)
    server.hp[full], server.hp[hurt] = 1080, 500
    del server.hp[dead]
    server.log.clear()
    advance(g, "CASTLE_AGE")
    assert server.hp[full] == 1800 and server.hp[hurt] == 1220            # + 720, the loss stays
    assert any(c.startswith(f"aoe building {full} 1800 8 10 ") for c in server.log)
    assert not any(dead in c for c in server.log if "players get" not in c)
    assert not any(c.startswith(("fill ", "summon ")) for c in server.log)   # the same design, the same target


def test_the_feudal_age_gives_the_palisade_walls_and_gates_their_feudal_age_hit_points():
    server, g = setup(age=0)
    g.stock["wood"] = 200
    build.wall(g, "Steve", "PALISADE_WALL", (14, 16))
    build.wall(g, "Steve", "PALISADE_WALL", (19, 16))
    gate = build.gate(g, "Steve", "PALISADE_GATE", (15, 16))
    for s in g.sites:
        build.rise(g, s, math.inf)
    wall = next(s for s in g.sites if s["name"] == "PALISADE_WALL")
    uuids = {s["name"]: combat.target_uuid([s["footprint"][0], s["footprint"][2], s["footprint"][1], s["footprint"][3]])
             for s in (wall, gate)}
    server.hp[uuids["PALISADE_WALL"]], server.hp[uuids["PALISADE_GATE"]] = 100, 240
    advance(g, "FEUDAL_AGE")
    assert server.hp[uuids["PALISADE_WALL"]] == 200 and server.hp[uuids["PALISADE_GATE"]] == 400
    assert any(c.startswith(f"aoe building {uuids['PALISADE_GATE']} 400 2 4 ") for c in server.log)


def test_no_change_in_the_imperial_age_for_a_stone_wall():
    server, g = setup(age=2)
    uuid, = walls(server, g, 16, 1)
    server.hp[uuid] = 900
    server.log.clear()
    advance(g, "IMPERIAL_AGE")
    assert server.hp[uuid] == 900 and not any(c.startswith("aoe building ") for c in server.log)
