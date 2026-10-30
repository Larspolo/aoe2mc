"""Live replay: the idle time of a villager counts only up to its next record command (#4063). In de-64.3 most idle
time went to villagers that the record never commands again: they died in the game or worked on with no command."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_eco import vill  # noqa: E402


def move(t, i):
    return dict(time=t, player=1, kind="move", objects=[i], tile=[1.0, 1.0])


def replay_of(timeline):
    r = replay.Replay(Fake(), data(timeline), ai=True)
    r.grid()
    return r


def test_the_idle_time_up_to_the_next_command_counts():
    r = replay_of([move(30_000, 1)])
    vill(r, "VILLAGER_MALE", 1, 1)
    r.idle_time(0)
    r.idle_time(20_000)
    assert r.idled[1] == 0                                      # no command yet: it can still be dead or at work
    r.idle_time(30_000)
    assert r.idled[1] == 30


def test_a_villager_with_no_later_command_adds_nothing():
    r = replay_of([move(10_000, 1)])
    vill(r, "VILLAGER_MALE", 1, 1)
    r.idle_at = r.told_at = 20_000                              # the last count: after its last command
    r.idle_time(600_000)
    assert r.idled[1] == 0
    assert r.idle_text(1) == "0:00"


def test_a_spawn_keeps_its_idle_time_when_its_record_id_comes():
    r = replay_of([move(25_000, 7)])
    v = vill(r, "VILLAGER_FEMALE", 1, -1)                       # at a gather point: no record ID yet
    r.idle_time(0)
    r.idle_time(20_000)
    r.units[7] = r.units.pop(-1)                                # unit() adopts it at its first command
    r.idle_time(30_000)
    assert r.idled[1] == 30 and v.uuid not in r.waiting


def test_a_command_in_a_jump_ends_the_wait():
    r = replay_of([move(100_000, 1), move(400_000, 1)])
    vill(r, "VILLAGER_MALE", 1, 1)
    r.idle_time(0)
    r.idle_time(10_000)
    r.idle_at = 300_000                                         # the jump in run(): the skipped time adds nothing
    r.idle_time(310_000)
    assert r.idled[1] == 20
