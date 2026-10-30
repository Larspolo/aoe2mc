"""Pause and speed change of a running replay (#685), with a fake clock and a fake RCON."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


class Clock(Fake):
    """A fake clock and RCON: the real time at which each chat event arrives."""
    def __init__(self):
        super().__init__()
        self.now, self.at = 0.0, {}

    def command(self, cmd):
        if cmd.startswith("tellraw") and (m := re.search(r"\bt\d+", cmd)):     # a chat event, not a view text
            self.at[m[0]] = round(self.now, 3)
        return super().command(cmd)

    def sleep(self, s):
        self.now += s


def chats(*times):
    return [{"time": t, "player": 1, "kind": "chat", "text": f"t{t}"} for t in times]


def run(times, poll, speed=1.0):
    game = Clock()
    stats = replay.Replay(game, data(chats(*times))).run(speed, clock=lambda: game.now, sleep=game.sleep, log=None,
                                                           poll=lambda c: poll(c, game.now))
    return game, stats


def test_a_speed_change_plays_the_later_events_faster():
    def poll(control, now):
        if now >= 60:
            control["speed"] = 4.0
    game, stats = run([30000, 60000, 100000, 140000], poll)
    assert game.at == {"t30000": 30, "t60000": 60, "t100000": 70, "t140000": 80}    # 40 s of game time: 10 s
    assert stats["events"] == 4 and len([c for c in game.sent if c.startswith("tellraw")]) == 4   # none twice


def test_a_pause_moves_the_later_events():
    def poll(control, now):
        control["paused"] = 20 <= now < 30
    game, _ = run([10000, 30000, 50000], poll, speed=2.0)
    assert game.at == {"t10000": 5, "t30000": 15, "t50000": 35}        # 25 s at 2x, and the pause of 10 s


def test_a_pause_stops_the_walking_units_of_the_plugin():
    r = replay.Replay(Fake(), data([]), ai=True)
    r.control, r.units, r.moving = {"speed": 1.0, "paused": True}, {7: replay.types.SimpleNamespace(
        uuid="u", name="VILLAGER")}, {7: 5000}
    assert r.retime(1000, 0.0, 2.0) == (3000, 2.0)                     # game time stops at 1 s + 2 s
    assert r.game.sent == ["attribute u minecraft:movement_speed base set 0.0"]
    r.control["paused"] = False
    assert r.retime(3000, 2.0, 12.0) == (3000, 12.0)                   # the pause adds no game time
    assert r.game.sent[-1].startswith("attribute u minecraft:movement_speed base set 0.")
