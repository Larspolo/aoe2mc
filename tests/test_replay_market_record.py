"""Live replay: the market trades of a recorded game change the estimate as the step-by-step sums say (#4130, #3938). Fake RCON."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import market  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

import aoe2mc  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
TRADES = ("buy", "sell")
TIMES = (1400000, None)     # ms: after the first 5 trades, and the end of the record (None)


@pytest.fixture(scope="module")
def timeline():
    return aoe2mc.read_timeline(REC)


def replay_of(events):
    d = data(events, n=480)
    d["players"]["2"]["arch"] = "western"       # data() has "meso", which buildings.ARCH lacks
    r = replay.Replay(Fake(), d)
    for e in events:
        r.commands(e)
    return r


def until(timeline, t):
    return [e for e in timeline if t is None or e["time"] <= t]


def expected(r, events):
    """The step-by-step sums of the trades: the gold, the resources and the rates, with market.price()."""
    rates, change = dict(market.RATES), {}
    for e in events:
        if e["kind"] not in TRADES:
            continue
        p, res, buy = e["player"], e["resource"].lower(), e["kind"] == "buy"
        g = SimpleNamespace(rates=rates, techs=set(r.upgrades(p, e["time"])), data=r.data, player=p)
        gold = market.price(g, res, buy)
        c = change.setdefault(p, dict.fromkeys(("gold", "food", "wood", "stone"), 0))
        c["gold"] += -gold if buy else gold
        c[res] += market.LOT if buy else -market.LOT
        rates[res] = min(max(rates[res] + (market.STEP if buy else -market.STEP), market.LIMITS[0]), market.LIMITS[1])
    return change, rates


@pytest.mark.parametrize("t", TIMES)
def test_the_trades_change_the_estimate_as_the_sums_say(timeline, t):
    events = until(timeline, t)
    with_trades = replay_of(events)
    without = replay_of([e for e in events if e["kind"] not in TRADES])
    change, rates = expected(with_trades, events)
    for p in (1, 2):
        for res in ("gold", "food", "wood", "stone"):
            assert with_trades.stock[p][res] - without.stock[p][res] == change.get(p, {}).get(res, 0)
    assert with_trades.rates == rates
