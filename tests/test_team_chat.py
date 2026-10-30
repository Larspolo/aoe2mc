"""A /tm line of a person reaches the persons of the own and the allied players, not the enemies (#3553)."""
import shutil
import time

import pytest


@pytest.mark.mc
def test_team_chat_reaches_the_allies(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not paper_reachable():
        pytest.skip("Xvfb, xdotool or Paper is not available")
    import mc_shot
    from test_mc_check import mojang_reachable

    from game import run
    if not mojang_reachable():
        pytest.skip("Mojang is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version) as one, \
            mc_shot.Client(server.game_port, server.version, name="Bob") as ally, \
            mc_shot.Client(server.game_port, server.version, name="Cy") as enemy:
        for client, name in ((one, "aoe2mc"), (ally, "Bob"), (enemy, "Cy")):
            client.wait_join(lambda n=name: n in server.command("list").split(":", 1)[-1])
            client.wait_loaded(server)                # else the keys go to "Loading terrain" (#3889)
        for c in ("team add p1", "team add p2", "team add p3", "team join p1 aoe2mc", "team join p2 Bob",
                  "team join p3 Cy", "aoe allies p1,p2"):
            server.command(c)
        time.sleep(5)

        def tm(text):
            one.key("t")
            time.sleep(1)
            one.xdo("type", "--delay", 50, f"/tm {text}")
            one.key("Return")
            time.sleep(2)

        def seen(client, text):                       # the client log can lag behind the chat
            for _ in range(10):
                if text in client.text():
                    return True
                time.sleep(1)
            return False

        tm("allies go")                               # allied: the own and the allied persons
        assert seen(one, "<aoe2mc> allies go")
        assert seen(ally, "<aoe2mc> allies go")
        assert "allies go" not in enemy.text()
        server.command("aoe allies -")
        tm("own only")                                # no ally: vanilla, the own team only
        assert seen(one, "<aoe2mc> own only")
        assert "own only" not in ally.text()
        assert "own only" not in enemy.text()
