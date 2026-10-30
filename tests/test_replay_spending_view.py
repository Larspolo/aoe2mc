"""Live replay: the spent resources of each player in the book "Economy", up to the replay time (#4391, epic #4386)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page, pages  # noqa: E402


def game():
    return replay.Replay(Fake(), data([]), ai=True)


def vill(r, name, player, k):
    """A villager of the replay with uuid u<k>, as the timeline makes it."""
    v = gather.Villager(f"u{k}", (0.0, 0.0, 0.0))
    v.name, v.player, v.job = name, player, replay.start_job(name)
    r.units[k] = v
    return v


def total(name):
    return sum(train.COSTS[name].values())


def test_a_payment_shows_in_its_group_from_its_time_on():
    r = game()
    r.grid()
    vill(r, "VILLAGER_MALE", 1, 1)
    r.pay(1, "MILITIA", 5000)
    before = r.ecoview(4000)
    after = r.ecoview(6000)
    assert page(before, 0)[-4:] == ["Eco 0", "Mil 0", "Tech 0", "Build 0"]
    assert page(after, 0)[-4:] == ["Eco 0", f"Mil {total('MILITIA')}", "Tech 0", "Build 0"]
    assert "Spent:" in page(after, 0)


def test_a_repeat_with_no_new_payment_sends_nothing():
    r = game()
    r.grid()
    vill(r, "VILLAGER_MALE", 1, 1)
    r.pay(1, "MILITIA", 5000)
    r.ecoview(6000)
    assert r.ecoview(6000) == []
    assert r.ecoview(7000) == []


def test_a_player_with_spending_and_no_villager_gets_a_page():
    r = game()
    r.grid()
    vill(r, "VILLAGER_MALE", 1, 1)
    r.pay(2, "MILITIA", 1000)
    cmds = r.ecoview(2000)
    assert len(pages(cmds)) == 2
    assert page(cmds, 1)[-4:] == ["Eco 0", f"Mil {total('MILITIA')}", "Tech 0", "Build 0"]
