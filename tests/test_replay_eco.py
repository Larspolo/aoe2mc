"""Live replay: the villagers of each player on each kind of work (#3755)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def replay_of_map():
    r = replay.Replay(Fake(), data([]), ai=True)
    r.grid()                                                    # the crew of the looks (no start units here)
    return r


def vill(r, name, player, k):
    """A villager of the replay with uuid u<k>, as the timeline makes it."""
    v = gather.Villager(f"u{k}", (0.0, 0.0, 0.0))
    v.name, v.player, v.job = name, player, replay.start_job(name)
    r.units[k] = v
    return v


def test_villagers_count_by_work():
    r = replay_of_map()
    a, b, c = (vill(r, "VILLAGER_MALE", 1, k) for k in (1, 2, 3))
    r.look(a, "LUMBERJACK")
    r.look(b, "LUMBERJACK")
    r.look(c, "BUILDER")
    assert r.eco()[1] == {"food": 0, "wood": 2, "gold": 0, "stone": 0, "build": 1, "idle": 0}


def test_idle_and_player_two_have_own_counts():
    r = replay_of_map()
    a = vill(r, "VILLAGER_MALE", 1, 1)
    r.look(a, "LUMBERJACK")
    r.look(a, "none")
    vill(r, "VILLAGER_FEMALE", 2, 2)
    r.look(r.units[2], "FARMER")
    eco = r.eco()
    assert eco[1]["idle"] == 1 and eco[1]["wood"] == 0
    assert eco[2]["food"] == 1 and eco[2]["idle"] == 0


def test_a_start_villager_is_idle_and_a_profession_change_keeps_its_task():
    r = replay_of_map()
    vill(r, "VILLAGER_MALE", 1, 1)
    f = vill(r, "VILLAGER_MALE", 1, 2)
    r.look(f, "FORAGER")
    r.look(f, "FARMER")
    assert f.task == "FARMER" and r.eco()[1]["idle"] == 1 and r.eco()[1]["food"] == 1
