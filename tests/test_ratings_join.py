"""--balance (#5223): after the last join, the teams of the human players follow ratings.balance."""
import os
import sys
from types import SimpleNamespace

from game import lobby

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import ratings  # noqa: E402


def make(people, table, tmp_path, monkeypatch):
    monkeypatch.setattr(ratings, "RATING_FILE", str(tmp_path / "r.json"))
    ratings.keep(table)
    sent = []
    game = SimpleNamespace(people=people, seats=(), sides={})

    def choose(name, n):
        game.sides[name] = n
        return True
    game.choose = choose
    players = {str(n): {"team": None} for n in range(1, people + 2)}
    players[str(people + 1)]["team"] = 3                               # a bot
    g = SimpleNamespace(game=game, players=players, data={"balance": True, "players": players}, command=sent.append)
    monkeypatch.setattr(lobby.menu, "close", lambda g, p: None)
    return g, sent


def test_last_join_sets_the_teams(tmp_path, monkeypatch):
    table = {"A": 1400, "B": 1000, "C": 1100, "D": 1300}
    g, sent = make(4, table, tmp_path, monkeypatch)
    for n, name in enumerate(table, 1):
        lobby.choose(g, name, n)
        if n < 4:
            assert all(p["team"] is None for k, p in g.players.items() if k != "5")
    split = ratings.balance(table)
    assert {name: g.data["players"][str(n)]["team"] for n, name in enumerate(table, 1)} == split
    assert g.players["5"]["team"] == 3                                 # the bot keeps its team
    chat = " ".join(c for c in sent if c.startswith("tellraw @a "))
    for t in (1, 2):
        names = [x for x in table if split[x] == t]
        mean = sum(table[x] for x in names) / len(names)
        assert f"Team {t} (mean rating {mean:.0f})" in chat
        assert all(x in chat for x in names)


def test_one_human_changes_no_team(tmp_path, monkeypatch):
    g, sent = make(1, {"A": 1200}, tmp_path, monkeypatch)
    lobby.choose(g, "A", 1)
    assert g.players["1"]["team"] is None
    assert not any("Team 1" in c for c in sent)
