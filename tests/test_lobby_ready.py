"""The game of more people starts when all people clicked "Ready" in the lobby page (#5508)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import lobby  # noqa: E402
import menu  # noqa: E402
import run  # noqa: E402
from test_start_on_join import FakeGame, Side  # noqa: E402


class G:
    """A Gather with only the parts of the lobby page."""
    players, data = {"1": {}, "2": {}}, {}

    def __init__(self, game):
        self.game, self.menus = game, {}

    def command(self, cmd):
        return self.game.command(cmd)


def lobby_game(people):
    game = FakeGame()
    game.people, game.sides, game.wait, game.ready = people, {}, True, set()
    return game, G(game)


def test_start_waits_until_all_are_ready(monkeypatch):
    game, g = lobby_game(2)
    monkeypatch.setattr(lobby.ratings, "load", lambda: {})
    monkeypatch.setattr(lobby.ratings, "tab", lambda g: None)
    clicks = iter([[], [("Steve", lobby.READY)], [], [("Alex", lobby.READY)]])
    monkeypatch.setattr(menu, "clicks", lambda g: [g.menus[p](p, s, False) for p, s in next(clicks, [])])
    calls = []

    def sleep(s):
        if s == 0.5:
            calls.append(set(game.ready))
            game.joined = {"Steve", "Alex"}
    run.start_on_join(game, [Side(lambda: 0.0)], 2, sleep=sleep, g=g)
    assert calls == [set(), {"Steve"}, {"Steve"}, {"Steve", "Alex"}]            # no start with one person ready
    assert game.ready == {"Steve", "Alex"} and game.sent[-1] == "tick unfreeze"
    assert any(c.startswith("aoe menu Steve") for c in game.sent)      # the join opens the lobby page
    assert "aoe menu-close Alex" in game.sent


def test_ready_is_a_toggle_before_the_start_only(monkeypatch):
    game, g = lobby_game(2)
    monkeypatch.setattr(lobby.ratings, "load", lambda: {})
    monkeypatch.setattr(lobby.ratings, "tab", lambda g: None)
    assert lobby.ready(g, "Steve") and game.ready == {"Steve"}
    assert any(lobby.READY == slot and "1 / 2" in lore for slot, _, _, lore in lobby.items(g, "Steve"))
    assert lobby.ready(g, "Steve") and game.ready == set()
    game.wait = False
    assert not lobby.ready(g, "Steve")
    assert all(slot != lobby.READY for slot, *_ in lobby.items(g, "Steve"))


def test_one_person_starts_at_the_join():
    game = FakeGame()

    def sleep(s):
        if s == 0.5:
            game.joined = {"Steve"}
    run.start_on_join(game, [Side(lambda: 0.0)], 1, sleep=sleep, g=G(game))
    assert game.sent[-1] == "tick unfreeze" and not game.ready
