"""The key "team" of a technology: the allies get its keys "work" and "costs" too (Kasbah, Butalmapu, #4329).
Test data: monkeypatched train.BY_KEY lines, not the values of the data lines (owner, 2026-10-29, #4242)."""
import types

from test_train_castle import setup

import pytest
import train as plain_train          # civs.cost imports train by its plain name (not game.train)


def game(monkeypatch, team):
    """The Gather of player 1 and a bot Gather of player 2 (team: the same team or not) that researched the test data."""
    monkeypatch.setitem(plain_train.BY_KEY["work"], "TEST_WORK", ("CASTLE", 1.25))
    monkeypatch.setitem(plain_train.BY_KEY["costs"], "TEST_COST", [[("KNIGHT",), None, 0.85]])
    monkeypatch.setitem(plain_train.BY_KEY["team"], "TEST_WORK", True)
    monkeypatch.setitem(plain_train.BY_KEY["team"], "TEST_COST", True)
    server, g = setup("BRITONS", ages=3)
    g.players.update({"1": {**g.players["1"], "team": 1}, "2": {"civ": "FRANKS", "team": 1 if team else 2}})
    other = types.SimpleNamespace(player=2, techs=set())
    g.bots = [types.SimpleNamespace(g=other)]
    return g, other


@pytest.mark.parametrize("team", [True, False])
def test_the_research_of_an_ally_counts_and_of_an_enemy_not(monkeypatch, team):
    g, other = game(monkeypatch, team)
    knight, rate = plain_train.price(g, "KNIGHT"), plain_train.work(g, "CASTLE")
    other.techs |= {"TEST_WORK", "TEST_COST"}
    assert plain_train.work(g, "CASTLE") == pytest.approx(rate * 1.25 if team else rate)
    assert plain_train.price(g, "KNIGHT") == ({k: int(v * 0.85 + 0.5) for k, v in knight.items()} if team else knight)


def test_a_technology_with_no_team_key_stays_with_its_player(monkeypatch):
    g, other = game(monkeypatch, True)
    monkeypatch.delitem(plain_train.BY_KEY["team"], "TEST_WORK")
    other.techs.add("TEST_WORK")
    assert plain_train.work(g, "CASTLE") == 1
    g.techs.add("TEST_WORK")
    assert plain_train.work(g, "CASTLE") == pytest.approx(1.25)


def test_a_bot_reaches_the_research_of_its_allied_person(monkeypatch):
    g, other = game(monkeypatch, True)
    bot = types.SimpleNamespace(player=2, techs=set(), share=g, players=g.players)
    g.techs.add("TEST_WORK")
    assert plain_train.work(bot, "CASTLE") == pytest.approx(1.25)
