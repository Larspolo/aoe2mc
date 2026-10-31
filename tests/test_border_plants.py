"""The far corner of the selection border is the ground behind grass and flowers, as in fleet.pick() (#3082,
Border.java)."""
import shutil

import pytest


@pytest.mark.mc
def test_the_far_corner_of_the_border_is_the_ground_behind_plants(tiny_world, tmp_path):
    """A real client stands on a grass floor and looks over short grass and flowers at a ground cell behind them."""
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import time

    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.forceload()
        for c in ("forceload add 0 0", "fill -3 99 -2 3 99 12 grass_block", "fill -3 100 -2 3 104 12 air",
                  "fill -3 100 1 3 100 5 short_grass", "fill -1 100 3 1 100 4 poppy",
                  "tp aoe2mc 0.5 100 0.5 0 15"):          # the eye at 101.62 looks down to the ground at z 6
            game.command(c)
        time.sleep(2)
        assert game.command("aoe box aoe2mc 0 0 red").startswith("Box: 1")
        time.sleep(1.5)                                    # Border.tick() runs every 4 ticks
        out = game.command("aoe box-corner aoe2mc")
        assert out.strip() == "Corner: 0 6", out           # the ray of the player stopped on a plant at z 1 to 5
