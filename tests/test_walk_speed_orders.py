"""game/monk.py, game/bot.py: each walk order sets the AoE2 walk speed with the civilization bonus and the walk
technologies (train.speed), as a move order does: a relic order, a conversion order and the attack of a bot (#3120)."""
from test_bot_attack import armed, orders
from test_monk_convert import setup as convert_setup
from test_relics import setup as relic_setup

from game import ai, monk, train


def fervor_command(g, uuid):
    return ai.speed_command(uuid, "MONK", g.map.T, ai.NORMAL * train.speed(g, "MONK", uuid))


def test_a_relic_order_of_a_monk_with_fervor_walks_at_the_fervor_speed():
    server, g = relic_setup()
    g.techs.add("FERVOR")
    assert train.speed(g, "MONK", "monk") > 1
    assert monk.order(g, "Steve", (10, 6))
    assert fervor_command(g, "monk") in server.log


def test_a_conversion_walk_of_a_monk_with_fervor_walks_at_the_fervor_speed():
    server, g = convert_setup(("foe", "MILITIA", 2, 30.5))              # out of range: the monk walks first
    g.techs.add("FERVOR")
    assert monk.convert_order(g, {"monk"}, "foe")
    monk.convert(g, 0.25)
    assert fervor_command(g, "monk") in server.log


def test_a_bot_with_squires_attacks_at_the_squires_speed():
    server, me, b = armed(n=2, attack=0.0)
    b.g.techs.add("SQUIRES")
    b.fight()
    assert len(orders(server)) == 2
    for u in ("m0", "m1"):
        assert ai.speed_command(u, "MILITIA", b.g.map.T, ai.NORMAL * train.speed(b.g, "MILITIA", u)) in server.log
