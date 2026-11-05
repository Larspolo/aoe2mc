"""The achievements of a conversion, the explored map, a siege tower over a wall, a trade route and a challenge medal
(#5646): the events of achievements.event and achievements.explored, and siege_tower.wall."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402
import combat  # noqa: E402
import siege_tower  # noqa: E402

ROWS = [{"name": "CONVERT_MONK", "event": "convert MONK"},
        {"name": "BIG_MAP", "event": "explore", "tiles": 480, "part": 0.99},
        {"name": "OVER_WALL", "event": "siege tower wall"},
        {"name": "ROUTE", "event": "trade route"},
        {"name": "ANY_MEDAL", "event": "challenge medal"},
        {"name": "GOLD", "event": "challenge gold"}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"
WALL = sorted(combat.WALLS)[0]


@pytest.fixture(autouse=True)
def rows(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)


def game(share=None):
    sent = []
    g = SimpleNamespace(player=1, share=share, players={}, data={"objects": [], "players": {}}, fort_names={}, forts={})
    g.command = sent.append
    return g, sent


@pytest.mark.parametrize("name, key", [("convert MONK", "convert_monk"), ("trade route", "route"),
                                       ("siege tower wall", "over_wall"), ("challenge medal", "any_medal"),
                                       ("challenge gold", "gold")])
def test_each_event_grants_its_line_once(name, key):
    g, sent = game()
    achievements.event(g, g, name)
    achievements.event(g, g, name)
    assert sent == [GRANT + key]


@pytest.mark.parametrize("name", ["convert MILITIA", "challenge silver", "challenge bronze"])
def test_another_unit_or_medal_grants_nothing(name):
    g, sent = game()
    achievements.event(g, g, name)
    assert sent == []


def test_a_bot_gets_nothing():
    g, sent = game(share=object())
    achievements.event(g, g, "convert MONK")
    achievements.explored(g, 480, 480 * 480)
    assert sent == []


@pytest.mark.parametrize("n, part, granted", [(480, 0.99, True), (480, 0.98, False), (400, 1.0, False)])
def test_the_explored_part_of_a_large_map(n, part, granted):
    g, sent = game()
    achievements.explored(g, n, round(part * n * n))
    assert sent == [GRANT + "big_map"] * granted


@pytest.mark.parametrize("owner, cell, near", [(2, (12, 10), True), (2, (20, 10), False), (1, (12, 10), False)])
def test_a_tower_next_to_an_enemy_wall(owner, cell, near):
    g, _ = game()
    g.forts, g.fort_names = {"w": (8, 0, 8, 10, 4, 12)}, {"w": WALL}
    g.data["objects"] = [{"uuid": "w", "player": owner}]
    assert siege_tower.wall(g, cell) is near
