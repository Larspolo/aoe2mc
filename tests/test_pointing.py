"""game/gather.py: before a click, the player sees what the click picks, also far away (#989): Gather.point() shows a
small ring of dust in the color of the target, and hints.py names the target and the action in the action bar."""
import json
import math
import re
import shutil

import pytest
from test_gather import FakeServer, grid

from game import gather, hints, lang

FEET = {"s-1": (5.5, 64.0, 10.5), "foe": (5.5, 64.0, 50.5), "v-1": (20.5, 64.0, 20.5)}


def setup():
    """A flat 60 × 60 map (tile size 1): a militia, a villager, an enemy knight 40 blocks south of the militia, a tree,
    a town center of player 1 and Steve."""
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [0.5, 0.5]}
               for u, n, p in (("s-1", "MILITIA", 1), ("v-1", "VILLAGER_MALE", 1), ("foe", "KNIGHT", 2))]
    objects += [{"kind": "other", "name": "TREE_OAK", "tile": [30.5, 10.5]},
                {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [41.5, 41.5],
                 "footprint": [40, 40, 44, 44]}]
    server = FakeServer({u: {"Pos": p} for u, p in FEET.items()} | {"Steve": {}})
    return server, gather.Gather(server, grid([[64] * 60 for _ in range(60)], objects)).setup()


def aim(server, at, point):
    """Steve stands with his feet at (x, 64, z) = at and looks at the point (x, y, z)."""
    eye = (at[0], 64.0 + 1.62, at[1])
    dx, dy, dz = (point[i] - eye[i] for i in range(3))
    yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    server.entities["Steve"] = {"Pos": (at[0], 64.0, at[1]), "Rotation": (yaw, pitch)}
    server.log.clear()


def rings(log):
    """[(color, scale)] of the dust points in log that only Steve sees."""
    return [(m[1], m[2]) for c in log
            if (m := re.fullmatch(r"particle minecraft:dust\{color:(\S+),scale:(\S+)\} \S+ \S+ \S+ 0 0 0 0 1 force Steve",
                                  c))]


def test_the_mark_and_the_click_pick_the_same_enemy_40_blocks_away():
    server, g = setup()
    aim(server, (5.5, 9.5), (5.5, 65.0, 10.5))
    g.click("Steve")                                                   # select the militia
    assert g.selected == {"s-1"}
    aim(server, (7.5, 10.5), (5.5, 65.0, 50.5))
    g.point()
    assert {k: lang.plain(v) for k, v in g.pointing.items()} == {"Steve": "Enemy Knight · Right click: attack"}
    assert rings(server.log) == [(gather.POINT["enemy"], "2.0")] * gather.POINT_POINTS   # 40 blocks: larger dust
    assert hints.state(g, "Steve")[0] == "pointing"
    assert lang.plain(hints.state(g, "Steve")[1]) == "1 military unit · Enemy Knight · Right click: attack"
    server.log.clear()
    g.click("Steve")
    assert f"aoe attack @e[tag={gather.SELECT}] foe" in server.log


def test_without_an_army_the_enemy_is_no_target():
    server, g = setup()
    aim(server, (7.5, 10.5), (5.5, 63.9, 45.5))                        # nothing selected: the click picks the ground
    g.point()
    assert lang.plain(g.pointing["Steve"]) == "Ground"
    assert {c for c, _ in rings(server.log)} == {gather.POINT["ground"]}


def test_each_target_kind_has_its_name_action_and_color():
    server, g = setup()
    aim(server, (20.5, 17.5), (20.5, 65.0, 20.5))
    g.point()
    assert lang.plain(g.pointing["Steve"]) == "Villager · Right click: select"
    assert {c for c, _ in rings(server.log)} == {gather.POINT["own"]}
    g.click("Steve")
    g.point()
    assert lang.plain(g.pointing["Steve"]) == "Villager · Right click: build menu"
    aim(server, (30.5, 30.5), (30.5, 66.0, 10.5))                      # the tree, 20 blocks away
    g.point()
    assert lang.plain(g.pointing["Steve"]) == "Tree · Right click: gather"
    assert {c for c, _ in rings(server.log)} == {gather.POINT["resource"]}
    aim(server, (42.0, 30.5), (42.0, 64.0, 41.0))                      # the own town center
    g.point()
    assert lang.plain(g.pointing["Steve"]) == "Town Center · Right click: train"
    assert {c for c, _ in rings(server.log)} == {gather.POINT["own"]}


def test_no_player_sends_no_mark():
    server, g = setup()
    server.log.clear()
    server.command = lambda c: server.log.append(c) or ("There are 0 of a max of 20 players online: " if c == "list"
                                                        else "")
    g.point()
    assert g.pointing == {} and server.log == ["list"]


def test_paper_reads_the_unit_places_with_one_where_command():
    server, g = setup()
    g.paper, g.selected = True, {"s-1"}
    answers = {f"aoe where @e[type=!player,team=!] {k}": a for k, a in (
        (0, "Where 41: s-1 5.50 64.00 10.50 0 0, foe 5.50 64.00 50.50 0 0, other 1.00 64.00 1.00 0 0"),
        (40, "Where 41: deer 9.00 64.00 9.00 0 0"))}
    server.log.clear()
    server.command = lambda c: server.log.append(c) or answers.get(c, "")
    assert g.places() == {"s-1": (5.5, 64.0, 10.5), "foe": (5.5, 64.0, 50.5)}
    assert server.log == list(answers)


@pytest.mark.mc
def test_the_pointing_mark_works_on_paper(tiny_world, tmp_path):
    """Paper with the plugin: the places of `aoe where` give the enemy 40 blocks away as the target of the mark and of
    the click, and the mark commands work. No client here: look() is set."""
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        game.command("team add p2")
        for u, (x, z) in {"00000000-0000-0000-0000-00000000a001": (8.5, 8.5),
                          "00000000-0000-0000-0000-00000000a002": (8.5, 48.5)}.items():
            game.command(f'summon minecraft:zombie {x} 100 {z} {{UUID:{uuid_ints(u)},NoAI:1b,NoGravity:1b,'
                         f'PersistenceRequired:1b,Tags:["aoe2mc.p2"]}}')
            game.command(f"team join p2 {u}")
        g = gather.Gather(game, data).setup()
        g.soldiers = {"00000000-0000-0000-0000-00000000a001": "MILITIA"}
        g.enemies = {"00000000-0000-0000-0000-00000000a002": "KNIGHT"}
        g.selected = set(g.soldiers)
        places = g.places()
        assert set(places) == set(g.soldiers) | set(g.enemies), places
        eye, head = (10.5, 101.62, 8.5), (8.5, 101.0, 48.5)               # 2 blocks east of the militia
        n = math.dist(eye, head)
        d = tuple((head[i] - eye[i]) / n for i in range(3))
        kind, key, cells = g.target(eye, d, places)
        assert (kind, key) == ("enemy", "00000000-0000-0000-0000-00000000a002")
        answers = [game.command(c) for c in gather.marker(g.map, cells, "enemy", "@a", gather.POINT,
                                                            gather.POINT_POINTS, gather.POINT_SCALE)]
        assert all("<--[HERE]" not in a and "Unknown" not in a for a in answers), answers
        log = []
        g.command = lambda c: log.append(c) or game.command(c)
        g.look = lambda name: (eye, d)
        g.click("Steve")
        assert f"aoe attack @e[tag={gather.SELECT}] {key}" in log


def uuid_ints(u):
    """The int array of a UUID string, for the UUID tag of summon."""
    n = int(u.replace("-", ""), 16)
    return "[I;" + ",".join(str((n >> s & 0xFFFFFFFF) - ((n >> s & 0xFFFFFFFF) >> 31 << 32)) for s in (96, 64, 32, 0)) + "]"
