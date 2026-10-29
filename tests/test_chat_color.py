"""A normal chat line shows the name of a person in the color of its team pN, the AoE2 player color (#3681)."""
import re
import shutil
import time

import pytest


@pytest.mark.mc
def test_a_chat_name_has_the_team_color(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not paper_reachable():
        pytest.skip("Xvfb, xdotool or Paper is not available")
    import mc_shot
    from game import run
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version) as one:
        one.wait_join(lambda: "aoe2mc" in server.command("list").split(":", 1)[-1])
        one.wait_loaded(server)                               # else the keys go to "Loading terrain" (#3889)
        for c in ("team add p1", "team modify p1 color blue", "team join p1 aoe2mc"):
            server.command(c)
        time.sleep(3)
        one.key("t")
        time.sleep(1)
        one.xdo("type", "--delay", 50, "hello color")
        one.key("Return")
        for _ in range(10):
            lines = [x for x in server.server.log if "hello color" in x]
            if lines and "<aoe2mc> hello color" in one.text():
                break
            time.sleep(1)
        assert "<aoe2mc> hello color" in one.text()          # the form stays "<name> text" (JOINED, #1310)
        line = lines[-1]
        assert "<aoe2mc> hello color" in re.sub(r"\x1b\[[0-9;]*m", "", line)
        assert re.search(r"<\x1b\[[0-9;]*[1-9][0-9;]*maoe2mc", line), repr(line)   # a color code before the name
