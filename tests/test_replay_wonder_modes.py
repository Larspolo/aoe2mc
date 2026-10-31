"""Live replay of a Wonder Race or Defend the Wonder record: the wonder timer of the mode in the panel, the boss bar
and the summary (#4896). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
import wonder  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_regicide import texts  # noqa: E402

WONDER = {"time": 60000, "player": 2, "kind": "build", "type": 276, "name": "WONDER", "tile": [8.0, 8.0]}


def record(kind, start=False):
    d = data([], n=128)
    d["lobby"] = {"type": kind, "dataset": "Definitive Edition"}
    d["players"]["2"]["arch"] = "western"                       # a WONDER design of the arch
    d["objects"] = [{"kind": "unit", "name": "VILLAGER_M", "player": p, "tile": [2.5 * p, 2.5], "uuid": f"u{p}"}
                    for p in (1, 2)]                                   # the panel shows the players with units
    if start:
        d["objects"] += [{"kind": "building", "name": "WONDER", "player": 1, "footprint": [4, 8, 4, 8], "ref": 9}]
    return replay.Replay(Fake(), d)


def panel(r, t):
    return " ".join(texts(r.score_commands(t)))


def test_a_finished_wonder_starts_its_timer_in_a_wonder_race():
    r = record("Wonder Race")
    assert r.wonders == {}
    r.commands(WONDER)
    assert r.wonders == {2: 60000}
    years = wonder.RACE["wonder-race"]
    cmds = r.score_commands(70000)
    assert f"Player 2 (Aztecs) · Wonder {years} y" in " ".join(texts(cmds))
    assert f'bossbar add {wonder.bar(2)} ""' in cmds
    assert any("Wonder Race" in t for t in texts(r.summary_commands()))


def test_the_start_wonder_runs_from_the_start_in_defend_the_wonder():
    r = record("Defend the Wonder", start=True)
    assert r.wonders == {1: 0}
    total = wonder.RACE["defend-the-wonder"]
    assert f"Wonder {total - 2} y" in panel(r, 10000)            # 10 s: 2 years of 5 s
    assert any("Defend the Wonder" in t for t in texts(r.summary_commands()))


def test_a_random_map_game_has_no_wonder_timer():
    r = record("Random Map", start=True)
    r.commands(WONDER)
    assert r.wonders == {}
    cmds = r.score_commands(70000)
    assert "Wonder" not in " ".join(texts(cmds)) and not any("bossbar" in c for c in cmds)
