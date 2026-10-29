"""game/train.py: when the player advances to a new age, the complete own walls and gates get the hit points of that age
(#1372, combat.WALLS). A damaged wall keeps its lost hit points; a destroyed wall stays air."""
import math

from test_fortified_wall import setup, walls

from game import build, combat, train


def hp(name, age):
    return combat.wall(name, age).hp


def head(uuid, name, age):
    """The start of the plugin command of a wall: its hit points and armor in the age."""
    w = combat.wall(name, age)
    return f"aoe building {uuid} {w.hp} {w.melee} {w.pierce} "


def advance(g, age):
    train.research(g, {"name": age, "player": "Steve"})


def test_the_castle_age_gives_the_stone_walls_their_castle_age_hit_points():
    server, g = setup(age=1)
    full, hurt, dead = walls(server, g, 16, 3)
    assert any(c.startswith(head(full, "STONE_WALL", 1)) for c in server.log)
    server.hp[full], server.hp[hurt] = hp("STONE_WALL", 1), 500
    del server.hp[dead]
    server.log.clear()
    advance(g, "CASTLE_AGE")
    more = hp("STONE_WALL", 2) - hp("STONE_WALL", 1)
    assert server.hp[full] == hp("STONE_WALL", 2) and server.hp[hurt] == 500 + more   # the loss stays
    assert any(c.startswith(head(full, "STONE_WALL", 2)) for c in server.log)
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
    server.hp[uuids["PALISADE_WALL"]], server.hp[uuids["PALISADE_GATE"]] = 100, hp("PALISADE_GATE", 0)
    advance(g, "FEUDAL_AGE")
    assert server.hp[uuids["PALISADE_WALL"]] == 100 + hp("PALISADE_WALL", 1) - hp("PALISADE_WALL", 0)
    assert server.hp[uuids["PALISADE_GATE"]] == hp("PALISADE_GATE", 1)
    assert any(c.startswith(head(uuids["PALISADE_GATE"], "PALISADE_GATE", 1)) for c in server.log)


def test_no_change_in_the_imperial_age_for_a_stone_wall():
    server, g = setup(age=2)
    uuid, = walls(server, g, 16, 1)
    server.hp[uuid] = 900
    server.log.clear()
    advance(g, "IMPERIAL_AGE")
    assert hp("STONE_WALL", 3) != hp("STONE_WALL", 2) or \
        server.hp[uuid] == 900 and not any(c.startswith("aoe building ") for c in server.log)
