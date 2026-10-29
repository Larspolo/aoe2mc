#!/usr/bin/env python3
"""
A guided owner check of a live replay (#1123): play to 5 real seconds before each moment, pause, wait for a player,
teleport the player to the place, play the moment at speed 1, pause, ask the question in the chat, go on.

Usage:
    python3 game/watch.py WORLD --watch STAGES [--speed 4] [--out ANSWERS.json]

STAGES is a JSON list of stages, or a text (a ticket body) with one line per moment:
    Watch: MM:SS | place | question            (MM:SS can be "end": the end of the replay)
    Task: what the owner does | question       (a stage without a time, for example the jumps)
A JSON stage: {"name", "at" (MM:SS, ms or "end"), "where", "speed" (default 1), "what", "ask"} or {"task", "ask"}.
A place: "chopper" (a villager that chops wood near a town center), "unit:NAME" (the first live unit whose name
starts with NAME, for example unit:SCOUT), "building:NAME" (a building whose name has NAME) or "tile:X,Y".
The guide prints READY, JOINED, PLACE, ASK, ANSWER and DONE lines; the `human` skill waits for them.
The answers come from the chat (the server log). "more" plays the moment again for 30 s.
"""
import argparse
import json
import math
import os
import re
import sys
import time

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import replay  # noqa: E402
import run  # noqa: E402

CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(?:\x1b\[[0-9;]*m)?(\w{1,16})(?:\x1b\[[0-9;]*m)?> (.*)$")   # the name in its team color (#3681, #3889)
LEAD = 5                    # real seconds of play before the moment
WATCH = 30                  # real seconds of play after the moment, then the question
JUMP = 120                  # a wait longer than this (real seconds) jumps; a shorter one plays, so units gather as usual


class Stop(Exception):
    """The last answer came before the end of the replay."""


def out(*a):
    print(*a, flush=True)


def players(game):
    return [p.strip() for p in game.command("list").split(":", 1)[-1].split(",") if p.strip()]


def say(game, msg, color="gold"):
    game.command(f"tellraw @a {json.dumps([{'text': '[check] ', 'color': 'aqua'}, {'text': msg, 'color': color}])}")


def stages(text, end=None):
    """The stages of a JSON list or of the `Watch:` and `Task:` lines of a text. end: the game time of the end (ms)."""
    try:
        got = json.loads(text)
    except ValueError:
        got = []
        for line in text.splitlines():
            m = re.match(r"\W*(Watch|Task):\s*(.*)", line)
            if not m:
                continue
            f = [p.strip() for p in m.group(2).split("|")]
            if m.group(1) == "Task" and len(f) == 2:
                got.append({"task": f[0], "ask": f[1]})
            elif m.group(1) == "Watch" and len(f) == 3:
                got.append({"at": f[0], "where": f[1], "what": f"{f[1]} at {f[0]}", "ask": f[2]})
    for k, s in enumerate(got):
        s.setdefault("name", str(k + 1))
        at = s.get("at")
        if at == "end":
            s["at"] = end
        elif isinstance(at, str):
            s["at"] = replay.aoe2mc.game_time(at)
        s.setdefault("what", s.get("task", "the moment"))
    return got


class Guide:
    """poll(control) of Replay.run next to the hotbar input of the replay (`input`, set by run.replay): the stages
    of the check. `r` is the Replay that runs now (run.replay sets it), for the places."""

    def __init__(self, game, stages, speed, answers, clock=time.monotonic, log=out):
        self.game, self.stages, self.speed, self.answers, self.clock, self.log = game, stages, speed, answers, clock, log
        self.input, self.r, self.k, self.state, self.t = None, None, 0, "play", 0.0
        self.server, self.seen = None, 0

    def chat(self):
        """The new chat lines of players since the last call: [(name, text)]. A restart (#979) gives a new log."""
        s = self.game.server
        if s is not self.server:
            self.server, self.seen = s, len(s.log)
        new, self.seen = s.log[self.seen:], len(s.log)
        return [m.groups() for ln in new if (m := CHAT.search(ln))]

    def target(self, where):
        """The place of a stage: (entity UUID or None, x, y or None, z, a point to stand toward or None)."""
        r = self.r
        if not r or not where:
            return None
        tcs = [((x0 + x1) / 2, (z0 + z1) / 2) for _, _, n, (x0, x1, z0, z1) in r.starts if "TOWN_CENTER" in n]
        kind, _, arg = where.partition(":")
        if kind == "chopper":
            best = None
            for i in r.working:
                v = r.units.get(i)
                if v is None or v.res != "wood" or (r.map and v.tree in r.map.farms):
                    continue
                d, tc = min(((math.dist((v.pos[0], v.pos[2]), c), c) for c in tcs), default=(math.inf, None))
                if best is None or d < best[0]:
                    best = (d, tc, v)
            return best and self.entity(best[2], best[1])
        if kind == "unit":
            v = next((v for v in list(r.units.values()) + [v for _, v in r.new]
                      if getattr(v, "name", "").startswith(arg.upper())), None)
            return v and self.entity(v, min(tcs, key=lambda c: math.dist((v.pos[0], v.pos[2]), c), default=None))
        if kind == "building":
            rect = next((rect for _, n, rect in [s[1:] for s in r.starts] + r.placed if arg.upper() in n), None)
            if rect:
                x0, x1, z0, z1 = rect
                return None, (x0 + x1) / 2, None, (z0 + z1) / 2, ((x0 + x1) / 2, z1 + 20)   # look from the south
        if kind == "tile":
            x, y = (float(v) for v in arg.split(","))
            return None, (x + 0.5) * r.T, None, (y + 0.5) * r.T, None
        return None

    def entity(self, v, toward):
        m = re.findall(r"-?\d+(?:\.\d+)?", self.game.command(f"data get entity {v.uuid} Pos").rsplit(":", 1)[-1])
        x, y, z = map(float, m[:3]) if len(m) >= 3 else v.pos
        return v.uuid, x, y, z, toward

    def place(self, stage):
        """Teleport the players 6 blocks from the place of the stage, toward a town center (open ground), facing it."""
        if not stage.get("where"):
            return
        g, got = self.game, self.target(stage["where"])
        if got is None:
            say(g, f"I cannot find {stage['where']} now: look around yourself.", "red")
            return
        uuid, x, y, z, toward = got
        d = math.dist((x, z), toward) if toward else 0
        ux, uz = ((toward[0] - x) / d, (toward[1] - z) / d) if d else (0.7, 0.7)
        px, pz = x + 6 * ux, z + 6 * uz
        g.command(f"tag @a add {replay.VIEWER}")                    # else overview(join=True) moves them up high
        g.command("gamemode adventure @a")                          # a double tap of Shift: spectator (Viewer.onInput, #1642)
        face = f"entity {uuid} eyes" if uuid else f"{x:.1f} ~ {z:.1f}"
        if y is None:                                               # no height: the top of the ground (Minecraft)
            g.command(f"spreadplayers {px:.1f} {pz:.1f} 0 1 false @a")
            g.command(f"execute as @a at @s run tp @s ~ ~3 ~ facing {face}")
        else:
            for p in players(g):
                g.command(f"tp {p} {px:.1f} {y + 3:.1f} {pz:.1f} facing {face}")
        if uuid:
            g.command(f"effect give {uuid} glowing 20 0 true")     # the owner finds it at once
        self.log(f"PLACE {stage['where']} at {x:.0f} {z:.0f}")

    def ask(self, stage):
        say(self.game, stage["ask"])
        say(self.game, "Type your answer in the chat: ok, or what is wrong. Type 'more' to see it longer.", "yellow")
        self.log(f"ASK {stage['name']}")

    def answer(self, stage, who, text, now):
        self.answers.append({"stage": stage["name"], "player": who, "time": round(now / 1000), "text": text})
        self.log(f"ANSWER {stage['name']}: <{who}> {text}")

    def __call__(self, control):
        if self.input:
            self.input(control)
        if self.k >= len(self.stages):
            return
        stage, now, real = self.stages[self.k], control.get("time", 0), self.clock()
        at, lead = stage.get("at"), LEAD * 1000 * self.speed
        if self.state == "play":
            if at is None:                                          # a stage that the owner does (the jumps)
                say(self.game, stage["task"])
                self.ask(stage)
                self.state = "answer"
            elif (at - lead - now) / 1000 / self.speed > JUMP:
                control["jump"] = at - lead
            elif now >= at - lead:
                control["paused"], self.state = True, "join"
                self.log(f"READY {stage['name']} at {now / 1000:.0f} s, players: {players(self.game)}")
                say(self.game, f"Paused {LEAD} s before {stage['what']}.")
        elif self.state == "join":
            if players(self.game):
                if self.t == 0:
                    self.t = real + (8 if self.k == 0 else 2)       # the first join: let the chunks load
                    self.log(f"JOINED {players(self.game)}")
                elif real >= self.t:
                    self.place(stage)
                    say(self.game, f"Look: {stage['what']}. It plays in 3 seconds.")
                    self.t, self.state = real + 3, "count"
        elif self.state == "count" and real >= self.t:
            speed = stage.get("speed", 1.0)
            control["paused"], control["speed"] = False, speed   # the owner: "4x went by too quick"
            self.t, self.state = real + max(0, at - now) / 1000 / speed + WATCH, "watch"   # the question WATCH s after the moment
        elif self.state == "watch" and real >= self.t:
            control["paused"] = True
            self.ask(stage)
            self.state = "answer"
        elif self.state == "answer":
            for who, text in self.chat():
                if text.strip().lower() == "more" and at is not None:
                    control["paused"] = False
                    self.t, self.state = real + WATCH, "watch"
                    return
                self.answer(stage, who, text, now)
                say(self.game, "Thank you. The replay continues to the next point.", "green")
                self.k, self.state, self.t = self.k + 1, "play", 0.0
                control["paused"], control["speed"] = False, self.speed
                if self.k == len(self.stages):                      # the last answer before the end: stop
                    raise Stop
                return
        if self.state != "answer":
            self.chat()                                             # only answers after a question count

    def last(self, end, sleep=time.sleep):
        """The replay ended before the last stage (the end of the replay): ask it now and wait for the answer."""
        if self.k >= len(self.stages):
            return
        self.k = len(self.stages) - 1
        stage = self.stages[self.k]
        self.ask(stage)
        self.chat()
        while not (got := self.chat()):
            sleep(0.5)
        self.answer(stage, *got[0], end)
        say(self.game, "Thank you. The check is done.", "green")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("--watch", required=True, metavar="STAGES", help="JSON stages or a text with Watch: lines")
    ap.add_argument("--speed", type=float, default=4.0, help="the speed between the moments (default 4)")
    ap.add_argument("--out", default="watch.json", help="the answers (JSON, default watch.json)")
    ap.add_argument("--version", default=run.mc_check.DEFAULT_VERSION, help="Minecraft version of the world")
    a = ap.parse_args(argv)
    with open(os.path.join(a.world, "aoe2mc.json")) as f:
        end = max(e["time"] for e in json.load(f)["timeline"])
    with open(a.watch) as f:
        todo = stages(f.read(), end)
    if not todo:
        sys.exit(f"no stages in {a.watch}")
    answers, stats = [], {}
    game = run.Game(a.world, a.version)
    try:
        game.start()
        guide = Guide(game, todo, a.speed, answers)
        out(f"SERVER localhost:{game.game_port}")
        try:
            stats = run.replay(game, a.world, a.speed, guide=guide)
        except Stop:
            stats = {"stopped after": todo[-1]["name"]}
            time.sleep(5)
        guide.last(end)
        time.sleep(5)
        errors = [ln for ln in game.server.log if re.search(r"ERROR|Exception", ln) and "minecraftservices" not in ln]
    finally:
        game.stop()
    with open(a.out, "w") as f:
        json.dump({"answers": answers, "stats": stats, "errors": errors[:30]}, f, indent=1, default=str)
    out(f"DONE {len(answers)} answers, {len(errors)} error lines")


if __name__ == "__main__":
    main()
