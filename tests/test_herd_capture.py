"""The capture of herdable animals in the game program (#1792): a unit near a Gaia herdable takes it; an own herdable
goes to an enemy only when no unit of its owner is near; the bot captures too. A fake RCON gives the positions."""
import json
import os
import re
import shutil
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import herd  # noqa: E402

T = 4
SHEEP, COW = "00000000-0000-0000-0000-00000000005e", "00000000-0000-0000-0000-0000000000c0"
SCOUT, MILITIA, VILL = ("00000000-0000-0000-0000-00000000000" + c for c in "123")
PLAYERS = {"1": {"color": "blue"}, "2": {"color": "red"}}


def bare(player, objects, **kw):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper, g.players = player, {"objects": objects}, types.SimpleNamespace(T=T), True, PLAYERS
    g.villagers, g.soldiers, g.selected, g.dead, g.bots = {}, {}, set(), {}, []
    g.prey = {o["uuid"]: o["name"] for o in objects if o["player"] in (0, player)}
    g.enemies = {o["uuid"]: o["name"] for o in objects if o["player"] not in (0, player)}
    g.sent, g.now = [], 0.0
    g.command, g.clock = g.sent.append, lambda: g.now
    g.set = lambda v, state: setattr(v, "state", state)
    vars(g).update(kw)
    return g


def near(tiles):
    return (10 * T + tiles * T, 70.0, 10 * T)


def game(sheep_owner=0, at=None):
    """Player 1 with a scout, its bot (player 2) with a militia, and one sheep at tile (10, 10)."""
    objects = [{"kind": "unit", "name": "SHEEP", "player": sheep_owner, "uuid": SHEEP, "tile": [10.0, 10.0]}]
    g = bare(1, objects, soldiers={SCOUT: "SCOUT_CAVALRY"})
    b = bare(2, objects, soldiers={MILITIA: "MILITIA"})
    g.bots = [types.SimpleNamespace(g=b)]
    pos = {SCOUT: (0.0, 70.0, 0.0), MILITIA: (200.0, 70.0, 200.0)} | (at or {})
    if sheep_owner:                                                  # in a team: `aoe where` gives its place
        pos[SHEEP] = near(0)
    g.where = lambda want: {u: p for u, p in pos.items() if u in want}
    return g, b, pos, objects[0]


def test_owner_rule():
    assert herd.owner({}, 0) == 0
    assert herd.owner({1: 1}, 0) == 1
    assert herd.owner({1: 1, 2: 3}, 1) == 1                          # one own unit near: the owner keeps it
    assert herd.owner({2: 1}, 1) == 2
    assert herd.owner({1: 2, 2: 3}, 0) == 2                          # the most units near
    assert herd.owner({2: 2, 3: 2}, 0) == 2                          # a tie: the lowest player


def test_a_gaia_sheep_goes_to_the_player_who_comes_near():
    g, b, pos, sheep = game()
    herd.tick(g)
    assert sheep["player"] == 0 and g.sent == []                     # the scout is far away
    pos[SCOUT] = near(herd.RANGE + 0.5)
    g.now = 1.0
    herd.tick(g)
    assert sheep["player"] == 0
    pos[SCOUT] = near(herd.RANGE - 0.5)
    g.now = 2.0
    herd.tick(g)
    assert sheep["player"] == 1
    assert g.sent == [f"tag {SHEEP} remove aoe2mc.p0", "tag " + SHEEP + " add aoe2mc.p1", f"team join p1 {SHEEP}",   # p0: #2916
                      f'data modify entity {SHEEP} CustomName.color set value "#2D2DF5"',
                      f"data modify entity {SHEEP} Color set value 11b"]   # blue wool
    assert SHEEP in g.prey and SHEEP not in b.prey and b.enemies[SHEEP] == "SHEEP"


def test_the_look_is_once_per_second():
    g, b, pos, sheep = game(at={SCOUT: near(1)})
    g.now = 0.5
    herd.tick(g)
    pos[MILITIA] = near(0)                                            # in reach, but no look before 1 s
    herd.tick(g)
    assert sheep["player"] == 1


def test_an_own_sheep_stays_while_an_own_unit_is_near_and_the_bot_takes_it():
    g, b, pos, sheep = game(sheep_owner=1, at={SCOUT: near(1), MILITIA: near(1)})
    g.selected = {SHEEP}
    hunter = gather.Villager(VILL, near(1))
    hunter.prey, hunter.state = SHEEP, "to_prey"
    g.villagers = {VILL: hunter}
    herd.tick(g)
    assert sheep["player"] == 1 and g.sent == []                     # two units of player 1 near: it stays
    pos[SCOUT] = pos[VILL] = near(5)
    g.now = 1.0
    herd.tick(g)
    assert sheep["player"] == 2                                      # the bot captures it
    assert g.sent[:2] == [f"tag {SHEEP} remove aoe2mc.p1", f"tag {SHEEP} add aoe2mc.p2"]
    assert f"data modify entity {SHEEP} Color set value 14b" in g.sent   # red wool
    assert SHEEP in b.prey and SHEEP not in b.enemies and SHEEP not in g.prey and g.enemies[SHEEP] == "SHEEP"
    assert SHEEP not in g.selected and f"tag {SHEEP} remove {gather.SELECT}" in g.sent
    assert hunter.prey is None and hunter.state == "idle"


def test_a_cow_has_no_wool_and_a_dead_herdable_or_a_deer_is_not_taken():
    g, b, pos, sheep = game(at={SCOUT: near(0)})
    sheep["name"] = "COW_A"
    g.data["objects"].append({"kind": "unit", "name": "DEER", "player": 0, "uuid": COW, "tile": [10.0, 10.0]})
    herd.tick(g)
    assert sheep["player"] == 1 and not any(" Color " in c for c in g.sent) and COW not in str(g.sent)
    sheep["player"], g.now, g.sent[:] = 0, 1.0, []
    b.dead[SHEEP] = (10, 10)                                          # the bot killed it: a carcass now
    herd.tick(g)
    assert sheep["player"] == 0 and g.sent == []


def test_no_capture_on_vanilla():
    g, b, pos, sheep = game(at={SCOUT: near(0)})
    g.paper = False
    herd.tick(g)
    assert sheep["player"] == 0


def int_array(u):
    """The NBT int array of a UUID string."""
    n = int(u.replace("-", ""), 16)
    return ",".join(str((n >> s & 0xFFFFFFFF) - ((n >> s & 0x80000000) << 1)) for s in (96, 64, 32, 0))


@pytest.mark.mc
def test_a_scout_walks_to_a_gaia_sheep_and_takes_it_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    x0, y, z0 = 1, 200, 1                                            # a floor in the air, inside the world border
    sheep = {"kind": "unit", "name": "SHEEP", "player": 0, "uuid": SHEEP, "tile": [(x0 + 30.5) / T, (z0 + 4.5) / T]}
    data["objects"].append(sheep)
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 36} {y - 1} {z0 + 10} stone_bricks")
        g = gather.Gather(game, data).setup()
        assert g.paper and SHEEP in g.prey
        game.command(f'summon sheep {x0 + 30.5} {y} {z0 + 4.5} {{UUID:[I;{int_array(SHEEP)}],NoAI:1b,Color:0b,'
                     'CustomName:{text:"Sheep",color:"#FFFFFF"}}')
        game.command(f'summon zombie {x0 + 2.5} {y} {z0 + 4.5} {{UUID:[I;{int_array(SCOUT)}],IsBaby:0b,'
                     'Tags:["aoe2mc.p1"]}')
        game.command(f"team join p1 {SCOUT}")
        g.soldiers[SCOUT] = "SCOUT_CAVALRY"
        herd.tick(g)
        assert sheep["player"] == 0                                    # 28 blocks away: 7 tiles
        out = game.command(f"aoe moveto {SCOUT} {x0 + 27.5} {y} {z0 + 4.5} 1.0")
        assert out.strip() == "Moved 1 units", out
        end = time.time() + 30
        while time.time() < end and sheep["player"] == 0:
            herd.tick(g)
            time.sleep(0.2)
        assert sheep["player"] == 1
        assert re.search(r"data: 11b$", game.command(f"data get entity {SHEEP} Color")), "blue wool"
        assert "#2D2DF5" in game.command(f"data get entity {SHEEP} CustomName")
        assert SHEEP in g.prey and SHEEP in g.where({SHEEP})          # in the team p1 now
