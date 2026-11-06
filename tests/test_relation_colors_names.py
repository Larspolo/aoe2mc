"""The mirror scoreboard of the relation colors keeps the sidebar names (#5884)."""
import shutil
import time

import pytest

from game import run


@pytest.mark.mc
def test_mirror_sidebar_keeps_the_display_names(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not shutil.which("Xvfb") or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    import mc_shot
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("scoreboard objectives add t5884 dummy")
        game.command("scoreboard objectives setdisplay sidebar t5884")
        game.command("scoreboard players set Gold t5884 3")
        game.command('scoreboard players display name Gold t5884 "Gold (0)"')
        game.command("aoe teamcolors aoe2mc p1=blue")
        time.sleep(2)
        first = game.command("aoe teamcolors aoe2mc show")
        game.command('scoreboard players display name Gold t5884 "Gold (2)"')   # a name change: tick() copies it
        time.sleep(2)
        second = game.command("aoe teamcolors aoe2mc show")
        game.command("aoe teamcolors aoe2mc off")
        main = game.command("aoe teamcolors aoe2mc show")                     # the main board again
    assert "Gold=Gold (0)" in first, first
    assert "Gold=Gold (2)" in second, second
    assert "Gold=Gold (2)" in main, main
