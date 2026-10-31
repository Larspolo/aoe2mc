"""The civilization key "sight_units" with several rules (#4791): an own rule and an ally rule add up for the player."""
from types import SimpleNamespace

import civs
import combat
import pytest

from game import civs as game_civs


@pytest.fixture
def player(monkeypatch):
    def set_rules(ally):
        ally_name = f"TESTALLY{len(ally)}{ally[0][0]}"     # its own key: Table.get caches a value by the team
        for m in {civs, game_civs}:                 # game/monk.py imports civs by its plain name (#4447)
            table = m.BY_KEY.setdefault("sight_units", {})
            monkeypatch.setitem(table, "TESTOWN", (("non-ranged units", 2),))
            monkeypatch.setitem(table.teams, ally_name, ally)
        civ = civs.Team("TESTOWN")
        civ.team = (ally_name,)                     # an ally rule joins the own rule
        monkeypatch.setattr(game_civs, "civ", lambda g, player=None: civ)
        return SimpleNamespace(data={"players": {"1": {"civ": "TESTOWN"}}}, player=1)
    return set_rules


def test_an_own_rule_and_an_ally_rule_that_match_add_their_tiles(player):
    g = player((("non-ranged units", 1),))
    assert game_civs.sight_units(g, "MILITIA", combat.stats("MILITIA")) == 2 + 1


def test_an_ally_rule_counts_for_the_player(player):
    g = player((("archers", 2),))
    assert game_civs.sight_units(g, "ARCHER", combat.stats("ARCHER")) == 2
