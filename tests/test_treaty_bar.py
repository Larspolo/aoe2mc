"""#2962: the boss bar "Treaty: M:SS left" of the treaty shows the seconds left, and it goes away at the end."""
import math

from test_bot_attack import armed

from game import treaty

BAR = "aoe2mc:treaty"


def bar_commands(server, start=0):
    return [c for c in server.log[start:] if c.startswith("bossbar ") and BAR in c]


def test_the_bar_shows_the_time_left_at_the_start():
    server, me, b = armed()
    treaty.start(me, 120.0)
    cmds = bar_commands(server)
    assert f'bossbar set {BAR} name "Treaty: 2:00 left"' in cmds
    assert f"bossbar set {BAR} value 120" in cmds
    assert f"bossbar set {BAR} max 120" in cmds


def test_a_tick_without_a_whole_second_change_adds_no_bar_command():
    server, me, b = armed()
    treaty.start(me, 120.0)
    start = len(server.log)
    treaty.tick(me, 1.0)
    assert f"bossbar set {BAR} value 119" in bar_commands(server, start)
    start = len(server.log)
    treaty.tick(me, 0.2)
    assert bar_commands(server, start) == []


def test_the_bar_goes_away_at_the_end_of_the_treaty():
    server, me, b = armed()
    treaty.start(me, 5.0)
    start = len(server.log)
    treaty.tick(me, 5.0)
    assert f"bossbar remove {BAR}" in bar_commands(server, start)


def test_a_treaty_with_no_end_has_no_bar():
    server, me, b = armed()
    treaty.start(me, math.inf)
    assert bar_commands(server) == []


def test_close_removes_the_bar_once_at_the_game_end():
    server, me, b = armed()
    treaty.start(me, 60.0)
    treaty.close(me)
    treaty.close(me)
    assert [c for c in server.log if c == f"bossbar remove {BAR}"] == [f"bossbar remove {BAR}"]
