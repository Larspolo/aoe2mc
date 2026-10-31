"""game/per.py: players-tribute-memory counts the tribute of a player since clear-tribute-memory, and
amount-tribute-inefficiency is the tribute fee of the player in percent (#5185). The map of test_per_players."""
import diplomacy as plain  # game/ modules import it by its plain name
from test_per_players import script


def send(monkeypatch, me, n, res, amount=100):
    monkeypatch.setattr(plain.market, "markets", lambda g: [1])
    me.stock[res] = 1000
    for _ in range(amount // plain.LOT):
        assert plain.send(me, None, n, res)


def test_a_tribute_raises_the_memory(monkeypatch):
    s, b, me = script()
    send(monkeypatch, me, 2, "gold", 200)
    assert s.check(("players-tribute-memory", 1, "gold", ">=", 200))
    assert s.check(("players-tribute-memory", 1, "wood", "==", 0))     # a resource with no tribute


def test_a_clear_sets_the_memory_of_the_resource_to_zero(monkeypatch):
    s, b, me = script()
    send(monkeypatch, me, 2, "gold", 100)
    send(monkeypatch, me, 2, "wood", 100)
    s.act(None, ("clear-tribute-memory", 1, "gold"))
    assert s.check(("players-tribute-memory", 1, "gold", "==", 0))
    assert s.check(("players-tribute-memory", 1, "wood", ">=", 100))  # the other resource keeps its count


def test_the_fee_is_30_percent_before_coinage():
    s, b, me = script()
    assert s.check(("up-resource-amount", "amount-tribute-inefficiency", "==", 30))


def test_coinage_lowers_the_fee_to_20_percent():
    s, b, me = script()
    b.g.techs = {"COINAGE"}
    assert s.check(("up-resource-amount", "amount-tribute-inefficiency", "==", 20))
