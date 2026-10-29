"""The shared start of a client check (#3831): a clean player, a safe place with loaded chunks, the health of a mob."""
import shutil
import time

import pytest


def needs_client():
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not paper_reachable():
        pytest.skip("Xvfb, xdotool or Paper is not available")
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not available")


def joined(server, name="aoe2mc"):
    return lambda: name in server.command("list").split(":", 1)[-1]


@pytest.mark.mc
def test_a_dead_player_starts_alive_the_next_time(tiny_world, tmp_path):
    needs_client()
    import mc_shot
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version, world=world) as c:
        c.wait_join(joined(server))
        server.command("gamemode survival aoe2mc")
        server.command("kill aoe2mc")
        time.sleep(2)
        server.command("save-all flush")
        time.sleep(2)
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version, world=world) as c:
        c.wait_join(joined(server))
        time.sleep(2)
        assert c.health(server, "@a[name=aoe2mc,limit=1]") == 20.0


@pytest.mark.mc
def test_a_far_place_shows_the_world_and_a_zombie_has_health(tiny_world, tmp_path):
    needs_client()
    import mc_shot
    from game import run
    from PIL import Image
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version, world=world) as c:
        c.wait_join(joined(server))
        server.command("gamemode creative aoe2mc")
        c.place(server, 300, 120, 300, pitch=60)
        img = Image.open(c.shot(str(tmp_path / "far.png"))).convert("RGB")
        assert len(img.getcolors(1 << 24)) > 1, "only one color: the chunks did not load"
        assert "Summoned" in server.command("summon minecraft:zombie 300 120 302 {Tags:[\"z\"],NoAI:1b}")
        assert c.health(server, "z") == 20.0
