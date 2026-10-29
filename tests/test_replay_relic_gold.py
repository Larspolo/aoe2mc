"""Live replay: each relic in an own monastery gives monk.GOLD per AoE2 second to its player's estimate; a relic that a
monk carries gives none (#4011). Fake RCON."""
from test_replay_relic_monastery import CHURCH
from test_replay_relic_pickup import MONK, RELIC, play

import monk
import replay

RELIC2 = dict(RELIC, ref=31, tile=[5.5, 11.5])


def at_home(r, ref, player):
    r.relics[ref].update(home=(30, 42, 40, 52), monk=None, player=player)


def test_two_relics_in_a_monastery_give_their_gold_in_60_seconds():
    r, _ = play([], [MONK, RELIC, RELIC2, CHURCH], end=1000)
    at_home(r, 30, 1)
    at_home(r, 31, 1)
    before, t0 = r.resources(1)["gold"], r.relic_at
    r.relic_income(t0 + 60000)
    gold = int(2 * monk.GOLD * 60)
    assert r.resources(1)["gold"] - before == gold > 0
    assert r.gathered[1]["gold"] == gold
    assert r.resources(2)["gold"] == replay.START["gold"]                # player 2 has no relic


def test_a_relic_that_a_monk_carries_gives_no_gold():
    r, _ = play([], [MONK, RELIC, CHURCH], end=1000)
    r.relics[30].update(monk=7, home=None, player=1)
    before, t0 = r.resources(1)["gold"], r.relic_at
    r.relic_income(t0 + 60000)
    assert r.resources(1)["gold"] == before
