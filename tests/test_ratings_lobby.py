"""The lobby item and the tab list show the rating of each Minecraft player (#5167); no rating shows nothing."""
import os
import sys
from types import SimpleNamespace

from game import lobby

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import ratings  # noqa: E402


def make(sides):
    sent = []
    game = SimpleNamespace(people=2, seats=(), sides=sides)
    return SimpleNamespace(game=game, players={}, command=sent.append), sent


def test_lobby_item_shows_the_rating():
    g, _ = make({"Steve": 1, "Alex": 2})
    lore = [it[3] for it in lobby.items(g, "Steve", {"Alex": 1016.4})]
    assert lore[1].endswith("Rating 1016")
    assert "Rating" not in lore[0]                     # Steve has no rating: no 1000


def test_tab_list_shows_ratings_only_of_rated_players(tmp_path):
    path = tmp_path / "r.json"
    ratings.keep({"Alex": 984.0}, str(path))
    g, sent = make({})
    ratings.tab(g, ratings.load(str(path)))
    assert "scoreboard objectives setdisplay list aoe_rating" in sent
    assert "scoreboard players set Alex aoe_rating 984" in sent
    assert not any("Steve" in c for c in sent)
