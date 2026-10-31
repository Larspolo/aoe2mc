"""The check of #5224 (epic #5165, item 4): on a real Paper server, two games of two people change the Elo ratings,
and the tab list, the lobby items and --balance show and use them. The ratings file is in tmp_path."""
import contextlib
import io
import json
import os
import re
import sys

import pytest

from game import conquest, gather, lobby

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import ratings  # noqa: E402  (conquest imports the plain module: patch that one)


def play(game, data, winner, loser):
    """One game: Minecraft player `winner` plays AoE2 player 1, `loser` player 2. All other players fall: player 1 wins."""
    game.sides.clear()
    game.sides.update({winner: 1, loser: 2})
    sent = []
    command = game.command
    game.command = lambda c: (sent.append(c), command(c))[1]
    try:
        g = gather.Gather(game, data).setup()
        for n in sorted({o["player"] for o in data["objects"]} - {0, 1}):
            conquest.defeat(g, n)
    finally:
        game.command = command
    assert g.ended == "Victory"
    return [json.loads(c[len("tellraw @a "):])["text"] for c in sent if c.startswith("tellraw @a ") and "→" in c]


@pytest.mark.mc
def test_two_games_change_and_show_the_ratings(tmp_path, monkeypatch):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios

    import aoe2mc
    from game import run
    monkeypatch.setattr(ratings, "RATING_FILE", str(tmp_path / "ratings.json"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.four_civs(str(tmp_path / "s.aoe2scenario")), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        game.people = 2
        chat = play(game, data, "Alpha", "Beta")
        assert ratings.load() == {"Alpha": 1016.0, "Beta": 984.0}
        assert chat == ["Alpha 1000 → 1016", "Beta 1000 → 984"]
        first = ratings.load()
        play(game, data, "Beta", "Alpha")
        second = ratings.load()
        assert all(abs(r - 1000) <= 2 for r in second.values())
        assert abs(sum(second.values()) - sum(first.values())) < 1e-9 and sum(first.values()) == 2000
        g = gather.Gather(game, data).setup()
        game.sides.clear()
        game.sides.update({"Alpha": 1, "Beta": 2})
        ratings.tab(g)
        for name, r in second.items():
            assert re.search(rf"{name} has {round(r)} \[Rating\]", game.command(f"scoreboard players get {name} aoe_rating"))
        lore = [it[3] for it in lobby.items(g, "Alpha")]
        assert lore[0] == f"You · Rating {round(second['Alpha'])}" and lore[1] == f"Taken by Beta · Rating {round(second['Beta'])}"
        table = {"Alpha": 1200.0, "Beta": 1100.0, "Gamma": 1000.0, "Delta": 900.0}
        ratings.keep(table)
        game.people = 4
        game.sides.clear()
        game.sides.update({"Alpha": 1, "Beta": 2, "Gamma": 3, "Delta": 4})
        g.data = {"balance": True}
        split = ratings.join(g)
        assert split == ratings.balance(table) == {"Alpha": 1, "Beta": 2, "Gamma": 2, "Delta": 1}
        assert {n: g.players[str(k)]["team"] for n, k in game.sides.items()} == split
