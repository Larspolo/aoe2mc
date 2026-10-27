"""The fog of the terrain of the view player on the live minimap (#1567, Minimap.java): black unexplored tiles, dark
explored tiles out of sight, no dot for a hidden enemy. Fake RCON; the server test needs a real client."""
import os
import re
import shutil
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

T = 4


def mob(uuid, player, x, y, name="VILLAGER_MALE"):
    return types.SimpleNamespace(uuid=uuid, player=player, name=name, pos=(x * T, 70.0, y * T))


def tiles(cmds, verb):
    """The tiles (x, y) of the `aoe minimap <verb>` runs."""
    out = set()
    for c in cmds:
        if c.startswith(f"aoe minimap {verb} "):
            for r in c.split()[3:]:
                y, x0, x1 = map(int, r.split(","))
                out |= {(x, y) for x in range(x0, x1 + 1)}
    return out


def fog(pov=1, ai=True):
    r = replay.Replay(Fake(), data([], n=128), ai=ai)               # 32 x 32 tiles
    r.pov = pov
    r.units = {1: mob("u1", 1, 5.5, 5.5), 2: mob("u2", 2, 25.5, 25.5)}
    return r


def test_runs_join_the_tiles_of_a_row_below_the_rcon_limit():
    assert replay.runs("c", {(1, 0), (2, 0), (3, 0), (5, 0), (2, 1)}) == ["c 0,1,3 0,5,5 1,2,2"]
    assert replay.runs("c", set()) == []
    many = {(x, y) for x in range(0, 200, 2) for y in range(10)}    # 1000 runs of 1 tile
    cmds = replay.runs("aoe minimap see", many)
    assert len(cmds) > 1 and all(len(c) <= replay.RCON_MAX for c in cmds) and tiles(cmds, "see") == many


def test_the_view_starts_the_fog_and_sends_the_tiles_in_sight():
    r = fog()
    cmds = r.fog()
    assert cmds.count("aoe minimap fog 4 32") == 1 and cmds[2].startswith("aoe minimap see")  # the start first
    sight = replay.seen(r.units.values(), [], 1, T)
    assert tiles(cmds, "see") == sight and (5, 5) in sight and (25, 25) not in sight
    assert tiles(cmds, "dim") == set()
    assert "aoe hide @a u2" in cmds                                   # the hidden enemy: no dot on the minimap either
    assert r.fog() == []                                              # no change: no command


def test_a_tile_out_of_sight_becomes_explored_and_in_sight_again():
    r = fog()
    old = replay.seen(r.units.values(), [], 1, T)
    r.fog()
    r.units[1].pos = (15.5 * T, 70.0, 5.5 * T)                        # 10 tiles east
    cmds = r.fog()
    new = replay.seen(r.units.values(), [], 1, T)
    assert tiles(cmds, "see") == new - old and tiles(cmds, "dim") == old - new
    assert not [c for c in cmds if c.startswith("aoe minimap fog")]
    r.units[1].pos = (5.5 * T, 70.0, 5.5 * T)                         # back: the old tiles are in sight again
    cmds = r.fog()
    assert tiles(cmds, "see") == old - new and tiles(cmds, "dim") == new - old


def test_the_tiles_outside_the_map_are_not_sent():
    r = fog()
    r.units[1].pos = (0.5 * T, 70.0, 0.5 * T)
    assert all(0 <= x < 32 and 0 <= y < 32 for x, y in tiles(r.fog(), "see"))


def test_an_ally_adds_its_sight_and_a_new_view_starts_again():
    r = fog()
    r.data["players"]["1"]["team"] = r.data["players"]["2"]["team"] = 1
    both = replay.seen(r.units.values(), [], 1, T) | replay.seen(r.units.values(), [], 2, T)
    assert tiles(r.fog(), "see") == both
    r.data["players"]["2"]["team"] = 2
    r.pov = 2
    cmds = r.fog()
    assert cmds[cmds.index("aoe minimap fog 4 32") + 1:] and tiles(cmds, "see") == replay.seen(r.units.values(), [], 2, T)
    assert tiles(cmds, "dim") == both - tiles(cmds, "see")            # player 2 saw the tiles of player 1 as an ally


def test_no_view_player_has_no_fog_and_removes_it():
    r = fog(pov=None)
    assert r.fog() == []
    r.pov = 1
    r.fog()
    r.pov = None
    assert r.fog() == ["aoe show @a u2", "aoe minimap fog off"]
    assert r.fog() == []


def test_vanilla_has_no_minimap_fog():
    assert not [c for c in fog(ai=False).fog() if "minimap" in c]


def mspt(game):
    """The mean milliseconds per tick of /tick query."""
    return float(re.search(r"Average time per tick: ([\d.]+)ms", game.command("tick query")).group(1))


@pytest.mark.mc
def test_the_minimap_draws_the_fog_on_a_server(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("item replace entity aoe2mc weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]")
        assert "Minimap: on" in game.command("aoe minimap on")
        time.sleep(3)
        before = mspt(game)
        base = game.command("aoe minimap tile 2 2").split()
        assert base[2] == "none" and base[3] != "0"                     # no fog: the base image
        assert "Minimap fog: 8 tiles" in game.command("aoe minimap fog 4 8")
        assert "Minimap see: 2 tiles" in game.command("aoe minimap see 0,0,1")
        assert "Minimap dim: 1 tiles" in game.command("aoe minimap dim 1,0,0")
        game.command("team add aoe_t2")
        game.command("team modify aoe_t2 color red")
        uuid = "00000000-0000-0000-0000-000000000617"                   # 1559 = 0x617
        game.command("summon minecraft:pillager 6 80 2 {UUID:[I;0,0,0,1559],NoAI:1b,NoGravity:1b}")
        game.command(f"team join aoe_t2 {uuid}")
        time.sleep(3)
        red = str(28 * 4 + 2)                                           # the map color of the red team
        assert game.command("aoe minimap tile 6 2").split()[2:] == ["seen", red]       # the dot of the unit
        assert game.command("aoe minimap tile 2 2").split()[2:] == ["seen", base[3]]   # in sight: the base color
        dim = game.command("aoe minimap tile 2 6").split()
        assert dim[2] == "explored" and int(dim[3]) & 3 == 3                           # the darkest shade
        assert game.command("aoe minimap tile 20 20").split()[2:] == ["unexplored", str(29 * 4 + 3)]
        assert game.command(f"aoe hide @a {uuid}").startswith("Hidden: 1")
        time.sleep(3)
        assert game.command("aoe minimap tile 6 2").split()[3] != red    # a hidden unit has no dot
        assert game.command("aoe minimap fog off").strip() == "Minimap fog: off"
        time.sleep(3)
        assert game.command("aoe minimap tile 20 20").split()[2] == "none"
        assert mspt(game) < before + 5                                  # the fog keeps the tick time
