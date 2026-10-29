"""#3375: the Game menu has the button "Pause" in slot 5. A click on it closes the menu and toggles the pause of
the game (pause.toggle, #3374); while the game is paused the lore of the button says "Continue"."""
from test_gather import FakeServer, grid

from game import diplomacy, gather, menu


def setup():
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 8 for _ in range(8)], [])).setup()
    return server, g


def click(server, g, slot):
    diplomacy.open_menu(g, "Steve")
    server.scores[menu.OBJECTIVE] = slot + 1
    g.clicks()


def test_the_game_menu_has_the_pause_button_in_slot_5():
    server, g = setup()
    diplomacy.open_menu(g, "Steve")
    assert diplomacy.PAUSE_SLOT == 5
    assert "5:clock:Pause:" in server.log[-1]


def test_a_click_on_pause_closes_the_menu_and_toggles_the_pause(monkeypatch):
    server, g = setup()
    calls = []
    monkeypatch.setattr(diplomacy.pause, "toggle", lambda gg, player: calls.append((gg, player)) or True)
    click(server, g, diplomacy.PAUSE_SLOT)
    assert calls == [(g, "Steve")]
    assert "aoe menu-close Steve" in server.log


def test_the_lore_says_continue_while_the_game_is_paused():
    server, g = setup()
    diplomacy.main(g).paused = True
    diplomacy.open_menu(g, "Steve")
    assert "5:clock:Pause:Continue" in server.log[-1]
