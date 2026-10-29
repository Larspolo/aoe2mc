"""An enemy unit in a vehicle out of sight has no dot on the minimap (#3674): the UUID of a unit is its root entity (the
boat of a fishing ship, the mount of a war elephant), and `aoe hide` hides its riders too (Passengers), so the living
rider of the team gets no dot (Minimap.java) and does not show in the world."""
import shutil
import time

import pytest

BOAT, RIDER = "00000001-0000-0002-0000-000300000004", "00000001-0000-0002-0000-000300000005"


@pytest.mark.mc
def test_a_hidden_boat_hides_the_dot_of_its_rider(tiny_world, tmp_path):
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
        for c in ("team add p7", "team modify p7 color red", "team add p8", "team modify p8 color blue",
                  "team join p8 aoe2mc"):
            game.command(c)
        game.command("execute positioned 18 0 18 positioned over motion_blocking run summon oak_boat ~ ~ ~ "
                     "{UUID:[I;1,2,3,4],Passengers:[{id:\"minecraft:zombie\",NoAI:1b,PersistenceRequired:1b,"
                     "UUID:[I;1,2,3,5]}]}")
        for u in (BOAT, RIDER):
            game.command(f"team join p7 {u}")
        assert "Minimap: on" in game.command("aoe minimap on")
        assert "Minimap fog: 8 tiles" in game.command("aoe minimap fog 4 8 p8")
        time.sleep(3)
        red = str(28 * 4 + 2)
        assert game.command("aoe minimap tile 18 18 p8").split()[2:] == ["unexplored", red]   # the rider: a dot
        assert "Hidden: 1 entities" in game.command(f"aoe hide @a[team=p8] {BOAT}")   # the unit UUID: the boat
        time.sleep(3)
        assert game.command("aoe minimap tile 18 18 p8").split()[3] != red                  # no dot of the rider
        assert "Shown: 1 entities" in game.command(f"aoe show @a[team=p8] {BOAT}")
        time.sleep(3)
        assert game.command("aoe minimap tile 18 18 p8").split()[3] == red                  # in sight again
