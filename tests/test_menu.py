"""Chest menus of the game program (#619): game/menu.py and the commands "aoe menu", "aoe menu-close" of the plugin."""
import re
import shutil
from urllib.parse import unquote

import pytest

from game import menu


class Game:
    """A fake server: the scores of aoe_menu, and the commands that it got."""

    def __init__(self, scores=None):
        self.sent, self.scores, self.menus = [], dict(scores or {}), {}

    def command(self, c):
        self.sent.append(c)
        m = re.fullmatch(r"scoreboard players (get|reset) (\S+) aoe_menu", c)
        if m and m.group(1) == "reset":
            self.scores.pop(m.group(2), None)
        elif m:
            return (f"{m.group(2)} has {self.scores[m.group(2)]} [aoe_menu]" if m.group(2) in self.scores
                    else f"Can't get value of aoe_menu for {m.group(2)}; none is set")
        return "Menu: 1 players"


def test_command_encodes_the_texts():
    c = menu.command("Steve", "Town Center", [(0, "minecraft:villager_spawn_egg", "Villager", "50 food\n25 s"),
                                             (8, "book", "Loom: 50 gold", "")])
    assert c == ("aoe menu Steve Town%20Center 0:villager_spawn_egg:Villager:50%20food%0A25%20s "
                 "8:book:Loom%3A%2050%20gold:")
    args = c.split(" ")                                                # RCON splits at spaces: one item per argument
    assert len(args) == 6 and unquote(args[3]) == "Town Center"
    assert [unquote(f) for f in args[5].split(":")] == ["8", "book", "Loom: 50 gold", ""]


def test_clicks_go_to_the_handler_of_the_open_menu():
    g, got = Game({"Steve": 3, "Alex": 1}), []
    menu.show(g, "Steve", "Town Center", [(2, "villager_spawn_egg", "Villager", "")], lambda p, s: got.append((p, s)))
    assert g.sent[-1].startswith("aoe menu Steve Town%20Center 2:")
    assert menu.clicks(g) == [("Steve", 2)] == got                     # Alex has no open menu: not read
    assert g.scores == {"Alex": 1} and "scoreboard players reset Steve aoe_menu" in g.sent
    assert menu.clicks(g) == [] and got == [("Steve", 2)]              # the score is reset: one click, one call
    g.scores["Steve"] = 3
    assert menu.clicks(g) == [("Steve", 2)]                            # the menu stays open: the next click counts
    menu.close(g, "Steve")
    assert g.sent[-1] == "aoe menu-close Steve" and g.menus == {}
    g.scores["Steve"] = 3
    assert menu.clicks(g) == []


def test_gather_reads_the_menu_clicks():
    from game import gather
    g, got = Game({"Steve": 1}), []
    me = gather.Gather.__new__(gather.Gather)                          # only the parts that clicks() uses
    me.game, me.menus, me.sites, me.players = g, {}, [], {}
    menu.show(me, "Steve", "Menu", [(0, "stone", "Stone", "")], lambda p, s: got.append(s))
    me.clicks()
    assert got == [0] and "Steve" not in g.scores


@pytest.mark.mc
def test_menu_commands_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        menu.setup(game)
        assert "Menu" in game.command("scoreboard objectives list")
        good = menu.command("@a", "Town Center", [(0, "villager_spawn_egg", "Villager", "50 food"),
                                                  (53, "book", "Loom", "")])
        assert game.command(good).strip() == "Menu: 0 players"         # no player joined: nobody gets it
        for bad in ("54:book:x:", "0:no_such_item:x:", "0:air:x:", "x:book:x:", "0:book"):
            assert game.command(f"aoe menu @a T {bad}").strip() == f"Bad item: {bad}"
        assert game.command("aoe menu-close @a").strip() == "Closed: 0 menus"
