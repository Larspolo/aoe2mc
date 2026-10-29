"""Live replay: a monk with a relic that an ORDER sends to an own monastery puts the relic in and stays outside, and
Replay.relic_count counts the relics of each player (#4010). Fake RCON."""
from test_replay_relic_pickup import MONK, RELIC, order, play

CHURCH = {"kind": "building", "name": "MONASTERY", "player": 1, "ref": 40, "tile": [9.0, 11.5],
          "footprint": [30, 40, 42, 52]}
OTHER = dict(CHURCH, player=2, ref=41)


def home(t, target):
    return dict(time=t, player=1, kind="order", objects=[7], target=target, names=["MONK"])


def test_a_monk_puts_the_relic_into_its_monastery():
    r, sent = play([order(0, 7, "MONK"), home(15000, 40)], [MONK, RELIC, CHURCH], end=45000)
    assert r.relics[30]["home"] == (30, 42, 40, 52) and r.relics[30]["monk"] is None
    assert r.relic_count(1) == 1 and r.relic_count(2) == 0
    assert "kill @e[type=item_display,tag=aoe_relic_30]" in sent
    assert not any(7 in us for us in r.garrisons.values()) and 7 not in r.entering


def test_the_monastery_of_another_player_takes_no_relic():
    r, sent = play([order(0, 7, "MONK"), home(15000, 41)], [MONK, RELIC, OTHER], end=45000)
    assert r.relics[30]["monk"] == 7 and r.relic_count(1) == r.relic_count(2) == 0
    assert not any(c.startswith("kill ") and "aoe_relic_30" in c for c in sent)


def test_a_monk_with_no_relic_changes_no_count():
    r, sent = play([home(0, 40)], [MONK, RELIC, CHURCH])
    assert r.relics[30]["at"] == (22, 42) and r.relic_count(1) == 0 and not r.homing
