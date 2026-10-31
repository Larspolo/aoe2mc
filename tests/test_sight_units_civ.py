"""The civilization key "sight_units" (#4448): the own units of a group see more tiles (Macedonians, Antiquity Mode)."""
from types import SimpleNamespace

import civs
import combat
import pytest

from game import civs as game_civs


@pytest.fixture
def test_civ(monkeypatch):
    for m in {civs, game_civs}:                     # game/monk.py imports civs by its plain name (#4447)
        monkeypatch.setitem(m.BY_KEY.setdefault("sight_units", {}), "TESTCIV", (("non-ranged units", 2),))
    return lambda c: SimpleNamespace(data={"players": {"1": {"civ": c}}}, player=1)


def more(g, name):
    return game_civs.sight_units(g, name, combat.stats(name))


def test_a_melee_unit_of_the_civilization_sees_2_tiles_more(test_civ):
    assert more(test_civ("TESTCIV"), "MILITIA") == 2
    cmd = combat.sight_command("u", "MILITIA", 4, more=more(test_civ("TESTCIV"), "MILITIA"))
    assert cmd == f"aoe sight u {(combat.sight('MILITIA') + 2) * 4}"


def test_a_ranged_unit_and_another_civilization_keep_their_sight(test_civ):
    assert more(test_civ("TESTCIV"), "ARCHER") == 0
    assert more(test_civ("BRITONS"), "MILITIA") == 0
