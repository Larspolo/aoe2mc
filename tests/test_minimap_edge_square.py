"""A building square across the east or the south edge of map 0 shows its part on the map, as one across the west or
the north edge does (#3081): `Minimap.render()` clipped only the start corner, and `pixel()` gave -1 for the end."""
import shutil
import time

import pytest


def edge(inside, low, high):
    """The last block x with inside(x) true, between low (inside) and high (outside)."""
    while high - low > 1:
        mid = (low + high) // 2
        low, high = (mid, high) if inside(mid) else (low, mid)
    return low


@pytest.mark.mc
def test_a_square_across_each_edge_shows_its_part(tiny_world, tmp_path):
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
        game.command("team add p1")
        game.command("team modify p1 color red")
        assert "Minimap: on" in game.command("aoe minimap on")
        x_in = z_in = 6
        assert "outside" not in game.command(f"aoe minimap pixel {x_in} {z_in}")

        def inside(x, z):
            return "outside" not in game.command(f"aoe minimap pixel {x} {z}")
        east = edge(lambda x: inside(x, z_in), x_in, x_in + 8192)
        south = edge(lambda z: inside(x_in, z), z_in, z_in + 8192)
        west = -edge(lambda x: inside(-x, z_in), -x_in, -x_in + 8192)
        north = -edge(lambda z: inside(x_in, -z), -z_in, -z_in + 8192)

        def tile(x, z):
            return game.command(f"aoe minimap tile {x} {z}").split()[3]
        probes = [(east - 1, z_in), (x_in, south - 1), (west + 1, z_in), (x_in, north + 1), (east, z_in - 20)]
        time.sleep(3)
        before = [tile(*p) for p in probes]
        for x0, z0, x1, z1 in [(east - 3, z_in - 2, east + 5, z_in + 2), (x_in - 2, south - 3, x_in + 2, south + 5),
                               (west - 5, z_in - 2, west + 3, z_in + 2), (x_in - 2, north - 5, x_in + 2, north + 3),
                               (east + 10, z_in - 22, east + 20, z_in - 18)]:          # fully outside the map
            assert "Minimap buildings" in game.command(f"aoe minimap building {x0} {z0} {x1} {z1} p1")
        time.sleep(3)
        red = str(28 * 4 + 2)                                           # the map color of the red team
        after = [tile(*p) for p in probes]
        assert after[:4] == [red] * 4 != before[:4], (before, after)
        assert after[4] == before[4] != red                             # the square outside draws nothing
