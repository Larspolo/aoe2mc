"""Unique technology of the Portuguese (#4327): the castle of the Portuguese researches Circumnavigation in the Castle
Age. The ships train faster (the key "train_group") and the whole minimap becomes explored (the key "on_research":
fog.explore); the enemy units out of sight stay hidden."""
import pytest
from test_train_castle import menus, setup

from game import fog, train

CASTLE = (12, 4)
TECH = next(n for n, h in train.BY_KEY["on_research"].items() if "fog.explore" in h)


def label(g, name):
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_portuguese_researches_circumnavigation():
    server, g = setup("PORTUGUESE", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, TECH)}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, TECH) is None


def test_ships_train_faster():
    _, g = setup("PORTUGUESE", ages=3)
    before = train.seconds(g, "GALLEY", "DOCK"), train.seconds(g, "ARCHER", "ARCHERY_RANGE")
    g.techs.add(TECH)
    factor = train.BY_KEY["train_group"][TECH][1]
    assert train.seconds(g, "GALLEY", "DOCK") == pytest.approx(before[0] / factor)
    assert train.seconds(g, "ARCHER", "ARCHERY_RANGE") == pytest.approx(before[1])


def test_the_map_becomes_explored_and_enemy_units_stay_hidden():
    _, g = setup("PORTUGUESE", ages=3)
    state = vars(g).setdefault("fog", {"hidden": {"enemy"}, "at": None})
    fog.explore(g, None)
    n = g.data.get("map_size") or len(g.map.ground) // g.map.T
    assert state["explored"] == {(x, y) for x in range(n) for y in range(n)}
    assert state["hidden"] == {"enemy"}
    assert any(c.startswith("aoe minimap dim p1") for c in fog.minimap(g, state))
