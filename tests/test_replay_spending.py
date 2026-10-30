"""Live replay: the spent resources of each player, by group (economy, military, technologies, buildings), up to a game
time (#4390, epic #4386)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import build  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
from test_replay import Fake, data  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
END = 600000
GROUPS = ("economy", "military", "technologies", "buildings")


def make():
    return replay.Replay(Fake(), data([]))


def total(cost):
    return sum(cost.values())


def test_each_payment_counts_in_its_group_from_its_time_on():
    r = make()
    unit = "MILITIA"
    tech = "COINAGE"
    building = "HOUSE"
    r.pay(1, "VILLAGER_MALE", 100_000)
    r.pay(1, unit, 200_000)
    r.pay(1, building, 300_000)
    r.pay(1, tech, 400_000)
    assert r.spent(1, 400_000) == {"economy": total(train.COSTS["VILLAGER_MALE"]), "military": total(train.COSTS[unit]),
                                   "technologies": total(train.COSTS[tech]), "buildings": total(build.COSTS[building])}
    assert r.spent(1, 250_000) == {"economy": total(train.COSTS["VILLAGER_MALE"]), "military": total(train.COSTS[unit]),
                                   "technologies": 0, "buildings": 0}


def test_a_payment_after_t_does_not_count():
    r = make()
    r.pay(1, "VILLAGER_MALE", 500_000)
    assert r.spent(1, 499_999) == {g: 0 for g in GROUPS}


def test_another_player_has_nothing_spent():
    r = make()
    r.pay(1, "VILLAGER_MALE", 100_000)
    r.pay(1, "HOUSE", 100_000)
    assert r.spent(2, END) == {g: 0 for g in GROUPS}


@pytest.fixture(scope="module")
def events():
    pytest.importorskip("mgz")
    return aoe2mc.read_timeline(REC)


def test_the_spending_of_the_record_matches_the_resources_up_to_10_00(events):
    r = replay.Replay(Fake(), data(events))
    for e in sorted(events, key=lambda e: e["time"]):
        if e["time"] > END:
            break
        if e["kind"] == "research":
            r.learn(e)
        elif e["kind"] in ("queue", "build"):
            r.pay(e["player"], e["name"], e["time"])
    for p in (1, 2):
        spent = r.spent(p, END)
        paid = sum(spent.values())
        assert paid == sum(replay.START[k] for k in replay.START) - sum(r.resources(p).values())
        names = [n for _, n in r.learned.get(p, []) if not n.endswith(" Age")]
        assert spent["technologies"] == sum(total(train.COSTS[n]) for n in names if n in train.COSTS)
