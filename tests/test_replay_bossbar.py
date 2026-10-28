"""Live replay: a boss bar shows the game time, the speed and the progress (#684). Fake RCON and a fake clock."""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402


def play(timeline, speed=2, **kw):
    now = [0.0]

    def sleep(s):
        now[0] += s
    game = Fake()
    replay.Replay(game, data(timeline)).run(speed=speed, clock=lambda: now[0], sleep=sleep, log=None, **kw)
    return [c for c in game.sent if c.startswith("bossbar")]


def chat(t):
    return {"time": t, "player": 1, "kind": "chat", "text": "hi"}


def test_clock_commands():
    name, value, players = replay.Replay.clock_commands(754_300, 1_200_000, 2)
    assert name == 'bossbar set aoe2mc:replay name {"text": "12:34 · speed 2×"}'
    assert value == "bossbar set aoe2mc:replay value 754" and players == "bossbar set aoe2mc:replay players @a"
    assert '"End 20:00"' in replay.Replay.clock_commands(1_200_000, 1_200_000, 0.5, done=True)[0]
    assert "speed 0.5×" in replay.Replay.clock_commands(0, 0, 0.5)[0]


def test_the_bar_shows_the_time_once_per_game_second():
    timeline = [chat(0), chat(300), chat(900), build(t=1500), chat(65_000)]
    bar = play(timeline, bar=True)
    assert bar[:3] == ['bossbar add aoe2mc:replay ""', "bossbar set aoe2mc:replay color white",
                       "bossbar set aoe2mc:replay max 65"]
    names = [c.split(" name ")[1] for c in bar if " name " in c]
    assert names == ['{"text": "00:00 · speed 2×"}', '{"text": "00:01 · speed 2×"}', '{"text": "01:05 · speed 2×"}',
                     '{"text": "End 01:05"}']                          # 3 events in second 0: one update
    assert "bossbar set aoe2mc:replay value 65" in bar


def test_without_bar_no_bossbar_command():
    assert play([chat(0), chat(5000)]) == []


@pytest.mark.mc
def test_bossbar_commands_work_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        r = replay.Replay(game, data([chat(0), chat(2000)]))
        sent = []
        game_command = game.command

        def command(c):
            out = game_command(c)
            sent.append((c, out))
            return out
        game.command = command
        game.batch = lambda cmds: [command(c) for c in cmds]        # the answer of each command, no aoe batch (#2761)
        r.run(speed=4, log=None, bar=True)
        bars = [(c, out) for c, out in sent if c.startswith("bossbar")]
        assert len(bars) >= 9 and all(out.startswith(("Created", "Custom bossbar", "Nothing changed"))
                                     for c, out in bars), bars        # no player: "Nothing changed" for players @a
        assert "End 00:02" in game_command("bossbar list")
