"""A real client on the Paper server clicks a chest menu (#627): tools/mc_shot.py Client, game/menu.py, the plugin."""
import shutil
import time

import mc_shot
import numpy as np
import pytest
from test_mc_check import mojang_reachable

from game import menu


def test_slot_pixels_of_a_chest_menu():
    c = mc_shot.Client.__new__(mc_shot.Client)
    c.size = (1280, 720)                                               # GUI 426 x 240 at scale 3
    assert c.slot(0, 1) == (423, 240)                                  # (125 + 8 + 8) * 3, (54 + 18 + 8) * 3
    assert c.slot(4, 1) == (423 + 4 * 54, 240)
    assert c.slot(9, 2) == (423, (45 + 18 + 18 + 8) * 3)              # row 2 of 2: the screen is 18 higher


@pytest.mark.mc
def test_a_player_clicks_a_menu_and_it_stays_open(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    from PIL import Image

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    items = [(0, "villager_spawn_egg", "Villager", "50 food"), (13, "book", "Loom", "50 gold")]
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(5)                                                  # the world is drawn
        game.menus, got = {}, []
        menu.setup(game)
        assert menu.show(game, "aoe2mc", "Town Center", items, lambda p, s, shift: got.append(s)).strip() == "Menu: 1 players"
        time.sleep(2)
        for slot in (0, 13, 5, 0):                                     # slot 5 is empty: no click
            client.click(*client.slot(slot, 2))
            time.sleep(1)
            menu.clicks(game)
        img = np.asarray(Image.open(client.shot(str(tmp_path / "menu.png"))).convert("RGB"), np.float32)
        assert got == [0, 13, 0], got
        assert game.command("data get entity aoe2mc Inventory").endswith("[]")    # the player took nothing
        assert img.std() > 20
        assert game.command("aoe menu-close aoe2mc").strip() == "Closed: 1 menus"  # it was still open
