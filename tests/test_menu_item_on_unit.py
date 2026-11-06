"""game/gather.py: the Game menu and the "Go to" item on an own villager open their menu, not the unit click (#5881)."""
import diplomacy
import goto
from test_select_type import setup


class ItemServer:
    """The FakeServer of test_select_type with one menu item in the main hand of Steve."""

    def __init__(self, server, key):
        self.server, self.key = server, key

    def __call__(self, cmd):
        if cmd.startswith("execute if items entity Steve weapon.mainhand"):
            self.server.log.append(cmd)
            return "Test passed, count: 1" if f"{self.key}:1b}}" in cmd else "Test failed"
        return self.command(cmd)


def click_item(monkeypatch, module, key, opened):
    """Steve right clicks a villager with the item key: only the talk statistic counts. Returns the server log."""
    monkeypatch.setattr(module, "open_menu", lambda g, player: opened.append(player))
    server, g = setup()
    g.choose({"v-1"})
    fake = ItemServer(server, key)
    fake.command, server.command = server.command, fake
    server.scores["aoe_talk"] = 1
    try:
        names = g.inputs()
    finally:
        server.command = fake.command
    return server.log, names


def test_game_menu_item_on_a_villager_opens_the_menu(monkeypatch):
    opened = []
    log, names = click_item(monkeypatch, diplomacy, "aoe_game_menu", opened)
    assert opened == ["Steve"]
    assert "Steve" not in names                                  # no unit click
    assert not any(c.startswith("data get entity Steve Rotation") for c in log)   # no ray


def test_go_to_item_on_a_villager_opens_the_menu(monkeypatch):
    opened = []
    log, names = click_item(monkeypatch, goto, "aoe_goto", opened)
    assert opened == ["Steve"]
    assert "Steve" not in names
    assert not any(c.startswith("data get entity Steve Rotation") for c in log)
