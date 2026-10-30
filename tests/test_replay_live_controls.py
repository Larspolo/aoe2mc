"""The replay controls in a live replay (#4733, epic #4660): a jump back keeps the parts of the record that came
after the start, a jump forward stops at "newest event time − delay" with one chat line, and pause and speed never
take the replay past that time."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_live import DELAY, TIMELINE, Writer, read_lines  # noqa: E402

ALL = {e["text"] for e in TIMELINE}


class Game(Writer):
    """The fake server and record writer of test_replay_live; it also keeps each game time that the boss bar shows,
    with the newest event in the file and whether the file is complete at that moment."""

    def __init__(self, *a):
        super().__init__(*a)
        self.shown = []

    def command(self, cmd):
        if cmd.startswith(f"bossbar set {replay.BAR} name") and (m := re.search(r"(\d+):(\d\d)", cmd)):
            self.shown.append(((int(m[1]) * 60 + int(m[2])) * 1000, *self.state()))
        return super().command(cmd)

    def state(self):
        return max(e["time"] for e in read_lines(self.path)), not self.parts


def follow(tmp_path, poll, speed=1.0, when=(20.0, 40.0, 60.0)):
    """A live replay (replay.live, as run.py --replay --live) of TIMELINE in 4 parts; poll(control, game) plays the
    player. Returns the game, the replays made and the number of commands sent at each restart."""
    path = tmp_path / "game.aoe2record"
    k = len(TIMELINE) // 4
    parts = [TIMELINE[:k], TIMELINE[k:2 * k], TIMELINE[2 * k:3 * k], TIMELINE[3 * k:]]
    game = Game(str(path), parts[1:], when)
    path.write_text("".join(json.dumps(e) + "\n" for e in parts[0]))
    source = live.Source(str(path), DELAY, read=read_lines, clock=lambda: game.now, check=1.0, idle=30.0)
    d, made, restarts = data(source.first()), [], []

    def make():
        made.append(replay.Replay(game, d))
        return made[-1]
    replay.live(make, speed, 0, lambda: restarts.append(len(game.sent)), clock=lambda: game.now, sleep=game.sleep,
                log=None, poll=lambda control: poll(control, game), bar=True, more=source.more)
    return game, made, restarts


def played(sent):
    return {m[0] for c in sent if c.startswith("tellraw") and (m := re.search(r"\bt\d+", c))}


def behind(game):
    """Each game time that the boss bar showed before the end is at most "newest event time − delay"."""
    late = [(t, newest) for t, newest, complete in game.shown if not complete and t > newest - DELAY * 1000]
    assert not late, late


def test_a_jump_back_plays_the_later_parts_again(tmp_path):
    asked = []

    def poll(control, game):
        if game.now >= 45 and not asked:                    # after the second part: back to 0:10
            asked.append(control["time"])
            control["jump"] = 10000
    game, made, restarts = follow(tmp_path, poll)
    assert len(made) == 2 and len(restarts) == 1 and asked[0] > 10000
    assert played(game.sent[restarts[0]:]) == {e["text"] for e in TIMELINE if e["time"] > 10000}
    assert made[-1].data["timeline"] == TIMELINE
    behind(game)


def test_a_jump_forward_stops_at_the_delay(tmp_path):
    asked = []

    def poll(control, game):
        if game.now >= 5 and not asked:
            asked.append(control["time"])
            control["jump"] = 100000                          # far after "newest − delay" (0:12)
    game, made, _ = follow(tmp_path, poll)
    behind(game)
    assert len(made) == 1
    assert any("jump stops at the delay" in c for c in game.sent if c.startswith("tellraw"))
    assert played(game.sent) >= {e["text"] for e in TIMELINE if e["time"] > 12000}   # the later parts all play


def test_speed_and_pause_stay_behind_the_delay(tmp_path):
    def poll(control, game):
        control["speed"] = 4.0
        control["paused"] = 30 <= game.now < 50
    game, _, _ = follow(tmp_path, poll)
    behind(game)
    assert played(game.sent) == ALL
