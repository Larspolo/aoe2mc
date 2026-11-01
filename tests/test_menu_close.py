"""A menu that the player closed (Escape) stays closed (#5484): the plugin sets the score aoe_menu_closed, menu.clicks()
forgets the handler, so train.refresh does not open the menu again when the queue changes."""
import shutil
import time

import pytest

from game import menu


class Fake:
    def __init__(self, closed):
        self.closed, self.sent, self.menus = closed, [], {}

    def command(self, c):
        self.sent.append(c)
        if c.startswith("scoreboard players get") and c.endswith(menu.CLOSED):
            return f"aoe2mc has 1 [{menu.CLOSED}]" if self.closed else f"Can't get value of {menu.CLOSED} for aoe2mc"
        return "Can't get value"


@pytest.mark.parametrize("closed", [True, False])
def test_clicks_forgets_the_menu_only_when_the_player_closed_it(closed):
    g = Fake(closed)
    g.menus["aoe2mc"] = lambda p, s, shift: None
    menu.clicks(g)
    assert ("aoe2mc" in g.menus) != closed
    assert (f"scoreboard players reset aoe2mc {menu.CLOSED}" in g.sent) == closed


@pytest.mark.mc
def test_escape_closes_the_menu_and_a_refresh_keeps_it_closed(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    items = [(0, "villager_spawn_egg", "Villager", "50 food")]
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        client.wait_loaded(game)
        game.menus = {}
        menu.setup(game)
        menu.show(game, "aoe2mc", "Town Center", items, lambda p, s, shift: None)
        time.sleep(2)
        menu.show(game, "aoe2mc", "Barracks", items, lambda p, s, shift: None)    # a new menu: no close of the player
        time.sleep(2)
        menu.clicks(game)
        assert "aoe2mc" in game.menus
        client.key("Escape")
        time.sleep(2)
        menu.clicks(game)
        assert "aoe2mc" not in game.menus
        assert game.command("aoe menu-close aoe2mc").strip() == "Closed: 0 menus"
