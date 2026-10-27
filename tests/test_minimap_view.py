"""The view square of each player on map 0 (#1762, Minimap.Frame of the plugin): a white outline around the place
of the player, only for that player. The start commands (fake RCON) and two real clients on a Paper server."""
import os
import re
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay_deaths import start  # noqa: E402

WHITE = str(8 * 4 + 2)          # map color SNOW, the normal shade


def test_the_square_is_about_one_aoe2_screen():
    assert 20 <= replay.FRAME <= 32                                     # tiles: 1920 x 850 pixels of 96 x 48 tiles


def test_the_replay_turns_the_square_on_on_paper():
    sent = start(ai=True)
    assert sent.count(f"aoe minimap frame {replay.FRAME * 4}") == 1
    assert sent.index("aoe minimap on") < sent.index(f"aoe minimap frame {replay.FRAME * 4}")   # above the dots
    assert not [c for c in start(ai=False) if "minimap" in c]           # vanilla has no plugin


def square(game, name):
    out = game.command(f"aoe minimap square {name}").split(":", 1)[1].split()
    return out if out == ["none"] else list(map(int, out))


def expect(game, x, z, h):
    """The pixels (x0, z0, x1, z1) of a square of side 2h around block (x, z), from "aoe minimap pixel"."""
    a = game.command(f"aoe minimap pixel {x - h} {z - h}").split(":")[1].split()
    b = game.command(f"aoe minimap pixel {x + h} {z + h}").split(":")[1].split()
    return [int(a[0]), int(a[1]), int(b[0]), int(b[1])]


@pytest.mark.mc
def test_each_player_sees_the_own_square_on_a_server(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as one, \
            mc_shot.Client(game.game_port, game.version, name="aoe2mc2") as two:
        def joined():
            return {"aoe2mc", "aoe2mc2"} <= set(game.command("list").split(":", 1)[-1].replace(",", " ").split())
        one.wait_join(joined)
        two.wait_join(joined)
        for name in ("aoe2mc", "aoe2mc2"):
            game.command(f"item replace entity {name} weapon.offhand with minecraft:filled_map[minecraft:map_id=0]")
            game.command(f"gamemode spectator {name}")                  # no fall: the place stays
        game.command("tp aoe2mc 20.5 80 20.5")
        game.command("tp aoe2mc2 44.5 80 40.5")
        assert "Minimap: on" in game.command("aoe minimap on")
        assert "Minimap frame: 16 blocks" in game.command("aoe minimap frame 16")
        time.sleep(3)
        a, b = square(game, "aoe2mc"), square(game, "aoe2mc2")
        assert a[:4] == expect(game, 20.5, 20.5, 8) and a[4] == int(WHITE)
        assert b[:4] == expect(game, 44.5, 40.5, 8) and b[4] == int(WHITE)
        game.command("tp aoe2mc 30.5 80 20.5")                         # the square follows the player
        time.sleep(3)
        assert square(game, "aoe2mc")[:4] == expect(game, 30.5, 20.5, 8)
        assert square(game, "aoe2mc2")[:4] == b[:4]                    # the other square stays
        game.command("tp aoe2mc -2000 80 -2000")                       # far outside the map: no square, no error
        time.sleep(3)
        assert square(game, "aoe2mc") == ["none"]
        edge = next(b for b in range(-300, 300) if "outside" not in game.command(f"aoe minimap pixel {b} {b}"))
        game.command(f"tp aoe2mc {edge + 1.5} 80 {edge + 1.5}")       # at the edge of pixel 0: clipped
        time.sleep(3)
        c = square(game, "aoe2mc")
        high = game.command(f"aoe minimap pixel {edge + 9.5} {edge + 9.5}").split(":")[1].split()
        assert c == [0, 0, int(high[0]), int(high[1]), int(WHITE)]
        assert "Minimap frame: off" in game.command("aoe minimap frame off")
        assert "Minimap: off" in game.command("aoe minimap off")
        time.sleep(2)
        log = open(os.path.join(game.folder, "logs", "latest.log")).read()
        assert not re.search(r"\bat aoe2mc\.", log)                       # no stack trace of the plugin
