"""game/per.py: the logic facts xor and xnor (as in AoE2 DE, #5042). Setup as test_per_rules.py."""
import pytest
from test_bot_gather import bot_map

from game import per
from game.bot import train


def run(text, steps=1, **stock):
    server, me, b = bot_map()
    b.g.stock.update(stock)
    s = per.Script(per.parse(text), b)
    for _ in range(steps):
        s.step()
    return s, b, server


def queued(b):
    return [e["name"] for q in b.g.queues.values() for e in q]


def test_xor_fires_when_exactly_one_fact_is_true():
    food = train.price(bot_map()[2].g, "VILLAGER_MALE")["food"]
    s, b, _ = run("(defrule (xor (true) (false)) => (train villager) (disable-self))", food=food)
    assert queued(b) == ["VILLAGER_MALE"]
    s, b, _ = run("(defrule (xor (true) (true)) => (train villager) (disable-self))", food=food)
    assert queued(b) == []


def test_xnor_is_the_opposite_of_xor():
    food = train.price(bot_map()[2].g, "VILLAGER_MALE")["food"]
    s, b, _ = run("(defrule (xnor (true) (true)) => (train villager) (disable-self))", food=food)
    assert queued(b) == ["VILLAGER_MALE"]
    s, b, _ = run("(defrule (xnor (true) (false)) => (train villager) (disable-self))", food=food)
    assert queued(b) == []


def test_xor_and_xnor_check_their_two_facts():
    s, b, _ = run("")
    assert s.check(("xor", ("true",), ("false",))) and not s.check(("xor", ("true",), ("true",)))
    assert s.check(("xnor", ("false",), ("false",))) and not s.check(("xnor", ("true",), ("false",)))


@pytest.mark.parametrize("name", ["xor", "xnor"])
def test_xor_and_xnor_take_exactly_two_facts(name):
    with pytest.raises(ValueError, match=f"{name} with 1 facts"):
        per.parse(f"(defrule ({name} (true)) => (do-nothing))")
