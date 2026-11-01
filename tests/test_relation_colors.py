"""The switch "Unique Player Colors" of the Game menu (#5510): the commands with a fake g."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import diplomacy  # noqa: E402
import relation_colors as rc  # noqa: E402

PLAYERS = {"0": {}, "1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}, "4": {"neutral": []}}


class G:
    def __init__(self, player=1):
        self.player, self.players, self.out, self.game = player, PLAYERS, [], None

    def command(self, c):
        self.out.append(c)
        return ""


def colors(cmd):
    return dict(x.split("=") for x in cmd.split()[3:])


def test_default_is_player_colors():
    assert not rc.on(G(), "Steve")


def test_switch_sends_relation_colors_for_the_person_only():
    g = G()
    rc.toggle(g, "Steve")
    assert g.out[-1].startswith("aoe teamcolors Steve ")
    c = colors(g.out[-1])
    assert c == {"p1": rc.COLORS["self"], "p2": rc.COLORS["enemy"], "p3": rc.COLORS["ally"], "p4": rc.COLORS["enemy"]}
    assert len({rc.COLORS["self"], rc.COLORS["ally"], rc.COLORS["enemy"]}) == 3
    rc.toggle(g, "Steve")
    assert g.out[-1] == "aoe teamcolors Steve off" and not rc.on(g, "Steve")


def test_refresh_after_stance_change(monkeypatch):
    g = G(2)
    rc.toggle(g, "Alex")
    g.out.clear()
    monkeypatch.setitem(PLAYERS, "4", {"neutral": [], "team": 2})
    rc.refresh(g)
    assert colors(g.out[-1])["p4"] == rc.COLORS["ally"]


def test_menu_button_toggles(monkeypatch):
    g = G()
    monkeypatch.setattr(diplomacy, "open_menu", lambda g, p: None)
    diplomacy.button(g, "Steve", diplomacy.COLORS_SLOT)
    assert rc.on(g, "Steve") and g.out[-1].startswith("aoe teamcolors Steve")
