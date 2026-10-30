"""
The live replay of a game of AoE2 DE that still runs (#4663, epic #4660): `run.py WORLD --replay --live RECORD`.
AoE2 DE writes the record file while the game runs. Minecraft cannot watch a file, so `Source` polls it: when the
file grows, it reads the record again (aoe2mc.record_timeline, as the converter does for aoe2mc.json) and gives
the new events to the replay (`Replay.play(more=...)`, #4662). It keeps the events of the last `delay` seconds of
game time back: the replay plays "newest event time − delay" or earlier, as the AoE2 DE spectator mode does.
The game ended when the record has its end (mgz match.completed: a player resigned, #4664) or when the file did not
grow for IDLE seconds (a crash, a draw, the players left): the source gives the rest, says the record is complete and
logs one line that says why.
"""
import os
import sys
import time

import aoe2mc

CHECK = 2.0                 # seconds of real time between two checks of the file size (a read takes about 2 s)
DELAY = 30.0                # seconds of game time that the live replay stays behind the game (--delay)
IDLE = 60.0                 # seconds of real time with no growth of the file: the game ended


class Source:
    """The events of the record at `path`, `delay` seconds of game time behind its newest event. `read(path)` gives
    the whole named timeline of the file (record_timeline) and may set `ended`; `turn`: the quarter turns of the world
    (aoe2mc.json)."""

    def __init__(self, path, delay=DELAY, turn=0, read=None, clock=time.monotonic, check=CHECK, idle=IDLE, log=None):
        if not os.path.isfile(path):
            raise OSError(f"--live: the record {path} does not exist")
        self.path, self.delay, self.clock, self.check, self.idle = path, delay * 1000, clock, check, idle
        self.log = log or (lambda m: print(m, file=sys.stderr))
        self.turn, self.read = turn, read or self.record
        self.ended, self.said = False, False             # the record has the end of the game; the end line is logged
        self.events, self.given, self.size = [], 0, None   # all events read, the number given, the file size read
        self.asked, self.grew = -float("inf"), clock()     # the real time of the last check and of the last growth

    def record(self, path):
        """The named timeline of the record file; `ended` when it has the end of the game."""
        state = {}
        events = aoe2mc.record_timeline(path, self.turn, state)
        self.ended = state.get("complete", False)
        return events

    def poll(self):
        """Read the file again if it grew. True when it grew."""
        size = os.path.getsize(self.path)
        if size == self.size:
            return False
        self.size, self.grew = size, self.clock()
        new = self.read(self.path)
        self.events = new if len(new) >= len(self.events) else self.events   # a cut read never takes events away
        return True

    def take(self, complete=False):
        """The events that the replay may play now, in the order of the record."""
        limit = float("inf") if complete else max((e["time"] for e in self.events), default=0) - self.delay
        k = self.given
        while k < len(self.events) and self.events[k]["time"] <= limit:
            k += 1
        out, self.given = self.events[self.given:k], k
        return out

    def first(self):
        """The events of the start of the replay."""
        self.poll()
        self.asked = self.clock()
        return self.take()

    def more(self):
        """Replay.play(more=...): (the new events, True when the record is complete)."""
        if self.clock() - self.asked < self.check:
            return [], False
        self.asked = self.clock()
        self.poll()
        idle = self.clock() - self.grew >= self.idle
        complete = self.ended or idle
        if complete and not self.said:
            self.said = True
            self.log("live: the game ended: the record is complete" if self.ended else
                     f"live: the record did not grow for {self.idle:g} s: the game ended")
        return self.take(complete), complete
