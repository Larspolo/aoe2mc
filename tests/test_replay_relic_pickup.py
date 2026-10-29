"""Live replay: a monk that an ORDER sends to a relic picks it up when it ends its walk: the pot block goes and a pot
rides the monk (#4009). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

MONK = {"kind": "unit", "name": "MONK", "player": 1, "uuid": "m1", "ref": 7, "tile": [2.5, 10.5]}
MONK2 = {"kind": "unit", "name": "MONK", "player": 1, "uuid": "m2", "ref": 8, "tile": [2.5, 12.5]}
VIL = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 9, "tile": [2.5, 12.5]}
RELIC = {"kind": "other", "name": "RELIC", "player": 0, "ref": 30, "tile": [5.5, 10.5]}


def order(t, i, name):
    return dict(time=t, player=1, kind="order", objects=[i], target=30, names=[name])


def play(timeline, objects, end=30000):
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += objects
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game.sent


def pickups(sent, uuid):
    return [c for c in sent if c.startswith("ride ") and c.endswith(f"mount {uuid}")]


def test_a_monk_picks_up_the_relic_at_the_end_of_its_walk():
    r, sent = play([order(0, 7, "MONK")], [MONK, RELIC])
    assert r.relics[30]["monk"] == 7 and r.relics[30]["at"] is None and 7 not in r.fetching
    assert any(c.startswith("fill 22 ") and c.endswith("air replace minecraft:decorated_pot") for c in sent)
    assert any("summon item_display" in c and "aoe_relic_30" in c for c in sent)
    assert len(pickups(sent, "m1")) == 1


def test_a_villager_picks_up_no_relic():
    r, sent = play([order(0, 9, "VILLAGER_MALE")], [VIL, RELIC])
    assert r.relics[30]["monk"] is None and r.relics[30]["at"] == (22, 42)
    assert not pickups(sent, "u1") and not any("decorated_pot" in c for c in sent)


def test_a_second_monk_does_not_take_a_carried_relic():
    r, sent = play([order(0, 7, "MONK"), order(15000, 8, "MONK")], [MONK, MONK2, RELIC])
    assert r.relics[30]["monk"] == 7 and not pickups(sent, "m2")


def test_another_order_ends_the_walk_to_the_relic():
    r, sent = play([order(0, 7, "MONK"), dict(time=100, player=1, kind="stop", objects=[7])], [MONK, RELIC])
    assert r.relics[30]["monk"] is None and not pickups(sent, "m1")
