"""The Celts capture enemy herdables also next to units of the owner (#1825), as in AoE2 (AoE2 wiki, "Herdable
animal": "Celts: Enemy herdables can be converted regardless of enemy units next to them")."""
import herd
from test_herd_capture import MILITIA, SCOUT, game, near


def play(civ):
    """An own sheep of player 1 with its scout near, and a militia of the bot (player 2, civ) near too."""
    g, b, pos, sheep = game(sheep_owner=1, at={SCOUT: near(1), MILITIA: near(1)})
    g.data["players"] = {"1": {"civ": "BRITONS"}, "2": {"civ": civ}}
    herd.tick(g)
    return sheep


def test_a_celt_unit_takes_an_enemy_sheep_next_to_a_unit_of_the_owner():
    assert play("CELTS")["player"] == 2


def test_another_civ_does_not_take_it():
    assert play("FRANKS")["player"] == 1


def test_owner_rule_of_the_celts():
    assert herd.owner({1: 3, 2: 1}, 1, {2}) == 2                     # more units of the owner: the Celt takes it too
    assert herd.owner({1: 1, 2: 1}, 1, {1, 2}) == 1                  # a Celt owner keeps it from another Celt
    assert herd.owner({1: 1, 2: 1, 3: 2}, 1, {2, 3}) == 3            # the Celt with the most units near
    assert herd.owner({1: 1, 3: 2}, 1, {2}) == 1                     # no Celt near: the old rule
    assert herd.owner({2: 1}, 0, {2}) == 2                           # a Gaia sheep: the old rule
