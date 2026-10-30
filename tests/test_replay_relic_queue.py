"""Live replay: a monastery ORDER soon after a relic ORDER keeps the walk to the relic; the monk picks the relic up and
then carries it home (#4517). Fake RCON."""
from test_replay_relic_monastery import CHURCH, home
from test_replay_relic_pickup import MONK, RELIC, order, pickups, play


def test_a_monastery_order_after_a_relic_order_brings_the_relic_home():
    r, sent = play([order(0, 7, "MONK"), home(1000, 40)], [MONK, RELIC, CHURCH], end=60000)
    assert len(pickups(sent, "m1")) == 1
    assert r.relics[30]["home"] == (30, 42, 40, 52) and r.relic_count(1) == 1
    assert not r.fetching and not r.homing and not r.queued


def test_a_move_still_ends_the_walk_to_the_relic():
    move = dict(time=1000, player=1, kind="move", objects=[7], tile=[2.5, 14.5])
    r, sent = play([order(0, 7, "MONK"), move], [MONK, RELIC, CHURCH])
    assert r.relics[30]["monk"] is None and not pickups(sent, "m1") and not r.fetching
