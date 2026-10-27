"""A click on an attack alert line takes the player to a view of the place (#1816): the plugin command "aoego"."""
import json
import os
import re
import shutil
import time

import pytest

from game import combat, gather, run

Y = 200                                                                # a floor in the air, inside the world border


def alert(game, data):
    """An enemy castle of player 2 shoots a unit of player 1 at 48 28: the alert "at 48 28" for team p1."""
    from test_damage import health
    game.command("forceload add 0 0 80 80")
    game.command(f"fill 0 {Y - 1} 0 79 {Y - 1} 79 stone_bricks")
    game.command("time set midnight")                                  # zombies burn in the sun
    for t in ("p1", "p2"):
        game.command(f"team add {t}")
    gather.Gather(game, data).setup()                                  # the online players join team p1
    game.command(f'summon zombie 48.5 {Y} 28.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
    game.command("team join p1 @e[tag=e]")
    game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")
    for c in combat.building(combat.target_uuid([20, 20, 36, 36]), "CASTLE", 2, (20, Y, 20, 35, Y + 40, 35)):
        game.command(c)
    end = time.time() + 30
    while health(game, "e") > 1000 - 50:
        assert time.time() < end, "the castle did not shoot"
        time.sleep(0.2)


def pos(game, name):
    out = game.command(f"data get entity {name} Pos")
    return [float(v) for v in re.findall(r"(-?[\d.]+)d", out)]


def log(game):
    with open(os.path.join(game.folder, "logs", "latest.log")) as f:
        return f.read()


@pytest.mark.mc
def test_a_click_on_the_alert_line_goes_to_a_view_of_the_place(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version, chat=True) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("deop aoe2mc")                                    # the click needs no operator rights
        game.command(f"tp aoe2mc 75 {Y} 75")                           # out of the range of the castle
        alert(game, data)
        time.sleep(2)
        assert "Go aoe2mc" not in log(game)
        game.command("aoego 48 28")                                    # RCON is no player: no teleport
        client.key("t")                                                # open the chat: its lines take clicks
        time.sleep(2)
        client.shot(str(tmp_path / "chat.png"))
        s, h = client.SCALE, client.size[1]
        client.click(100, h - 40 * s - 9 * s // 2)                     # the last line: 9 GUI pixels, 40 above the bottom
        time.sleep(2)
        client.key("Escape")
        time.sleep(1)
        client.shot(str(tmp_path / "view.png"))
        x, y, z = pos(game, "aoe2mc")
        flying = game.command("data get entity aoe2mc abilities.flying")
        text = log(game)
    assert "Go aoe2mc: 48" in text, text[-3000:]
    assert (int(x), int(z)) == (48, 40) and y >= Y + 12, (x, y, z)     # 12 blocks above and south of 48 28
    assert "1b" in flying, flying                                      # creative (run.py): it flies at the view


@pytest.mark.mc
def test_aoego_only_goes_to_an_alert_place_of_the_own_team(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    with run.Game(world) as game:
        alert(game, data)
        out = game.command("aoego 48 28")
        assert "a player" in out, out                                  # the console is no player
        assert "Go " not in log(game)
