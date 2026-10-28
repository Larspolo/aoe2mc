"""The fog of each player on the minimap of the game program (#2583, epic #2580): fog.minimap sends the sight of the
team of a Gather to its own fog on map 0 (`aoe minimap fog T N pN`, `see pN`, `dim pN`), and the plugin shows an enemy
building to a team only after a tile of it was in its sight (Minimap.java)."""
import os
import shutil
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import fog  # noqa: E402


def side(player, size=16):
    return types.SimpleNamespace(player=player, map=types.SimpleNamespace(T=4), data={"map_size": size})


def test_two_players_with_other_sights_get_other_runs():
    one, two = side(1), side(2)
    assert fog.minimap(one, {"tiles": {(1, 1), (2, 1)}}) == ["aoe minimap fog 4 16 p1", "aoe minimap see p1 1,1,2"]
    assert fog.minimap(two, {"tiles": {(9, 3)}}) == ["aoe minimap fog 4 16 p2", "aoe minimap see p2 3,9,9"]


def test_a_tile_out_of_sight_becomes_explored_and_only_changes_go_out():
    g, state = side(1), {"tiles": {(1, 1), (2, 1)}}
    fog.minimap(g, state)
    state["tiles"] = {(2, 1), (3, 1), (40, 1)}                         # (40, 1): outside the map
    assert fog.minimap(g, state) == ["aoe minimap see p1 1,3,3", "aoe minimap dim p1 1,1,1"]
    assert fog.minimap(g, state) == []                                 # no change: no command


def test_reveal_removes_the_fog_of_the_team_and_a_new_update_starts_it_again():
    sent = []
    g = side(2)
    g.command, g.fog = sent.append, {"hidden": set(), "at": None, "tiles": {(1, 1)}}
    fog.minimap(g, g.fog)
    fog.reveal(g)
    assert sent == ["aoe minimap fog off p2"] and "map" not in g.fog
    assert fog.minimap(g, g.fog)[0] == "aoe minimap fog 4 16 p2"


@pytest.mark.mc
def test_the_plugin_shows_an_enemy_building_after_the_team_saw_it(tiny_world, tmp_path):
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
        assert "Minimap: on" in game.command("aoe minimap on")
        assert "Minimap fog: 8 tiles" in game.command("aoe minimap fog 4 8 p8")
        assert "Minimap see: 2 tiles" in game.command("aoe minimap see p8 0,0,1")   # tiles (0, 0) and (1, 0)
        assert "Minimap buildings: 1" in game.command("aoe minimap building 16 16 24 24 p7")   # tiles (4, 4) to (5, 5)
        time.sleep(3)
        black = str(29 * 4 + 3)
        assert game.command("aoe minimap tile 2 2 p8").split()[2] == "seen"
        assert game.command("aoe minimap tile 18 18 p8").split()[2:] == ["unexplored", black]   # never seen: no square
        assert "Minimap see: 1 tiles" in game.command("aoe minimap see p8 4,4,4")
        time.sleep(3)
        red = str(28 * 4 + 2)
        assert game.command("aoe minimap tile 18 18 p8").split()[2:] == ["seen", red]   # the team saw it
        assert "Minimap dim: 1 tiles" in game.command("aoe minimap dim p8 4,4,4")
        time.sleep(3)
        dim = game.command("aoe minimap tile 18 18 p8").split()
        assert dim[2] == "explored" and int(dim[3]) == 28 * 4 + 3        # it stays known, in the dark shade
        assert game.command("aoe minimap tile 18 18").split()[2] == "none"   # the fog without a team stays off
        assert game.command("aoe minimap fog off p8").strip() == "Minimap fog: off"
