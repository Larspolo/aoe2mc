"""A chat line of a spectator (team spec) reaches the spectators only; a line of a player reaches all (#3554)."""
import shutil
import time

import pytest


@pytest.mark.mc
def test_a_spectator_chat_line_does_not_reach_the_players(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not paper_reachable():
        pytest.skip("Xvfb, xdotool or Paper is not available")
    import mc_shot
    from test_mc_check import mojang_reachable

    from game import run
    if not mojang_reachable():
        pytest.skip("Mojang is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version) as player, \
            mc_shot.Client(server.game_port, server.version, name="Bob") as spec:
        player.wait_join(lambda: "aoe2mc" in server.command("list").split(":", 1)[-1])
        spec.wait_join(lambda: "Bob" in server.command("list").split(":", 1)[-1])
        player.wait_loaded(server)                    # else the keys go to "Loading terrain" (#3889)
        spec.wait_loaded(server)
        for c in (*run.SPECTATORS, "team add p1", "team join p1 aoe2mc", "team join spec Bob"):
            server.command(c)
        time.sleep(5)

        def say(client, text):
            client.key("t")
            time.sleep(1)
            client.xdo("type", "--delay", 50, text)
            client.key("Return")
            time.sleep(2)

        say(spec, "scout here")                       # a spectator: the spectators only
        assert "[CHAT] <Bob> scout here" in spec.text()
        assert "scout here" not in player.text()
        say(player, "attack now")                     # a player: all persons, also the spectators
        assert "[CHAT] <aoe2mc> attack now" in player.text()
        assert "[CHAT] <aoe2mc> attack now" in spec.text()
