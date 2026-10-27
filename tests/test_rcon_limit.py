"""The RCON limit (#1647): the Minecraft RCON server closes the connection after a command longer than 1446 bytes,
and the game program stopped when the build menu grew past it. A long menu goes out in more commands, Rcon refuses a
long command before it sends it, and the fake servers of the tests fail on one."""
import pytest
from test_build_menu import villager_map

from game import build, menu, rcon


class Echo:
    """A fake server: the conftest fixture rcon_limit checks its commands."""

    def command(self, cmd):
        return cmd


def test_rcon_refuses_a_long_command_before_it_sends_it():
    client = rcon.Rcon.__new__(rcon.Rcon)
    sent = []
    client.sock = type("Sock", (), {"sendall": lambda self, b: sent.append(b)})()
    with pytest.raises(rcon.RconError, match=r"1447 bytes, the limit is 1446: say xxx"):
        client.command("say " + "x" * 1443)
    assert not sent and rcon.MAX == 1446


def test_a_long_menu_goes_out_in_more_commands_below_the_limit():
    items = [(s, "book", f"Item {s}", "1000 food · 1000 gold · 100 s · research\nmore text " * 2) for s in range(54)]
    cmds = menu.commands("Steve", "Town Center", items)
    assert len(cmds) > 1 and all(len(c.encode()) <= rcon.MAX for c in cmds)
    assert cmds[0].startswith("aoe menu Steve Town%20Center 53:") and all(c.startswith("aoe menu-add Steve Town%20Center ")
                                                                           for c in cmds[1:])
    specs = [x for c in cmds for x in c.split(" ")[4:]]
    assert sorted(specs) == sorted(menu.spec(it) for it in items)


def test_a_short_menu_stays_one_command():
    items = [(0, "villager_spawn_egg", "Villager", "50 food")]
    assert menu.commands("Steve", "Town Center", items) == [menu.command("Steve", "Town Center", items)]


def test_the_build_menu_is_longer_than_one_command_and_each_part_fits():
    _, g = villager_map()
    items = build.items(g)                                              # with the cost and time lore of the player
    assert len(menu.command("Steve", "Build", items).encode()) > rcon.MAX               # 1571 bytes in #1647
    assert all(len(c.encode()) <= rcon.MAX for c in menu.commands("Steve", "Build", items))


def test_a_fake_server_fails_on_a_long_command():
    assert Echo().command("say hi") == "say hi"
    with pytest.raises(AssertionError, match="RCON command of 1447 bytes"):
        Echo().command("say " + "x" * 1443)
