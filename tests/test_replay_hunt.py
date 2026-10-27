"""The hunted animal of the live replay dies (#1281): the first hunter at the carcass kills the animal entity, a second
ORDER on it sends no second kill, a jump kills it at once, and the carcass is never on a tree, bush or mine tile.
Fake clock and RCON."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay_gather import TREE, order  # noqa: E402
from test_replay_jump_team import SHEEP, run  # noqa: E402


def kills(r):
    return [c for c in r.game.sent if c.startswith("damage s1 ")]


def test_the_first_hunter_kills_the_animal_once():
    r = run([dict(order(0, 30), tile=[5.5, 10.5]), dict(order(60000, 30), tile=[5.5, 10.5])], [SHEEP], to=None)
    assert len(kills(r)) == 1 and not r.prey


def test_the_animal_lives_until_the_hunter_is_there():
    r = run([dict(order(0, 30), tile=[5.5, 10.5])], [SHEEP], to=None)
    i = next(k for k, c in enumerate(r.game.sent) if c.startswith("damage s1 "))
    assert any(c.startswith("tp u1 ") for c in r.game.sent[:i])       # it walked first


def test_a_jump_kills_the_hunted_animal_at_once():
    r = run([dict(order(0, 30), tile=[5.5, 10.5])], [SHEEP])
    assert len(kills(r)) == 1


def test_the_carcass_is_not_on_a_tree():
    r = run([dict(order(0, 30), tile=[5.5, 10.5])], [SHEEP, TREE], to=None)
    tile = r.hunted[30]
    assert tile != (5, 10) and max(abs(tile[0] - 5), abs(tile[1] - 10)) == 1 and r.map.resource(tile) == "food"
