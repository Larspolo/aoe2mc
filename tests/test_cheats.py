import json
import os
import shutil
import time

import pytest

from game import cheats, gather
from test_gather import FakeServer
from test_mc_check import mojang_reachable


def game(tiny_world, on):
    with open(os.path.join(tiny_world[0], "aoe2mc.json")) as f:
        data = json.load(f)
    server = FakeServer({})
    return server, gather.Gather(server, data, cheats=on, start={}).setup()


def test_lumberjack_gives_wood_with_cheats_on(tiny_world):
    server, g = game(tiny_world, True)
    log = "\n".join(server.log)
    assert "aoe cheats " in log and ",lumberjack," in log
    wood = cheats.CODES["lumberjack"]["wood"]
    server.scores["aoe_cheat"] = cheats.NAMES.index("lumberjack") + 1
    assert g.clicks() == []                                    # a cheat is no click
    assert g.stock["wood"] == wood and server.wood() == wood
    assert "aoe_cheat" not in server.scores                    # read once
    g.clicks()
    assert g.stock["wood"] == wood


def test_ninjalui_gives_each_resource_and_polo_answers(tiny_world):
    server, g = game(tiny_world, True)
    server.scores["aoe_cheat"] = cheats.NAMES.index("ninjalui") + 1
    assert cheats.clicks(g) == [("Steve", "ninjalui")]
    assert g.stock == cheats.CODES["ninjalui"]
    server.scores["aoe_cheat"] = cheats.NAMES.index("polo") + 1
    cheats.clicks(g)
    assert server.log[-1] == 'tellraw Steve {"text":"Fog of war: off"}'          # (#1390)


def test_no_cheat_with_cheats_off(tiny_world):
    server, g = game(tiny_world, False)
    assert not any("cheat" in c for c in server.log)           # the plugin knows no code: the text is chat
    server.scores["aoe_cheat"] = cheats.NAMES.index("lumberjack") + 1
    g.clicks()
    assert g.stock["wood"] == 0


def test_codes_are_sorted():
    assert list(cheats.CODES) == cheats.NAMES                  # one entry on each line, alphabetical (CLAUDE.md)


@pytest.mark.mc
def test_a_player_types_a_cheat_in_the_chat(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    gold = cheats.NAMES.index("robin hood") + 1
    with run.Game(world) as server, mc_shot.Client(server.game_port, server.version) as client:
        client.wait_join(lambda: "aoe2mc" in server.command("list").split(":", 1)[-1])
        time.sleep(5)
        server.cheats = False

        def say(text):
            client.key("t")
            time.sleep(1)
            client.xdo("type", "--delay", 50, text)
            client.key("Return")
            time.sleep(2)

        def score():
            return server.command(f"scoreboard players get aoe2mc {cheats.OBJECTIVE}")

        cheats.setup(server)                                   # cheats off: a normal chat message
        say("robin hood")
        assert "[CHAT] <aoe2mc> robin hood" in client.text()
        server.cheats = True
        cheats.setup(server)
        for text in ("Robin Hood ", "/robin hood"):
            say(text)
            assert f"has {gold} " in score(), (text, score())
            server.command(f"scoreboard players reset aoe2mc {cheats.OBJECTIVE}")
        assert client.text().count("robin hood") == 1, client.text()[-2000:]   # only the message without cheats
        assert "Unknown" not in client.text()[-2000:]
