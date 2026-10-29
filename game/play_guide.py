#!/usr/bin/env python3
"""
A chat guide for an owner play test on a running `game/run.py --play` server (#1674), as game/watch.py is for a replay:
the owner only plays and answers in the Minecraft chat.

Usage:
    python3 game/play_guide.py GAME_PORT WORLD STEPS.json [--out ANSWERS.json]

GAME_PORT: the port of "Join the server localhost:PORT". The guide finds the server folder of that port in `.cache/`
(its server.properties has the RCON port and password) and reads the chat from its `logs/latest.log`.
STEPS.json: a JSON list of steps {"name", "setup": [commands], "cheats": [codes], "task", "ask"}. A placeholder in a setup command:
"{NAME}" is the first object NAME of player 1 in aoe2mc.json, "{NAMEn}" that of player n: the target UUID of a
building (combat.target_uuid), the UUID of a unit. For example "{BARRACKS}", "{MILITIA1}", "{TOWN_CENTER2}".
A step gives the state that it needs with its setup commands (the age, resources), or with "cheats": the AoE2 cheat
codes (game/cheats.py NAMES, `game/run.py --cheats`) that the guide runs for the first player after the setup, so that
the owner does not type them (#2052). The guide sets the score aoe_cheat of the player, as the plugin does for a chat
code, and waits until cheats.clicks resets it before the next code. An unknown code stops the guide before the first
step. A Stone Wall needs the Feudal Age (build.AGE).
The guide waits for a player, then for each step runs the setup, says the task and the question in the chat and waits
for the answer. More chat lines in MORE seconds after the first one are one answer ("It worked, but the units" ...).
It prints JOINED, SETUP, ASK, ANSWER and DONE lines; the `human` skill waits for them.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                          "..", "tools")]
import cheats  # noqa: E402
import combat  # noqa: E402
import mc_check  # noqa: E402
from rcon import Rcon  # noqa: E402

CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(?:\x1b\[[0-9;]*m)?(\w{1,16})(?:\x1b\[[0-9;]*m)?> (.*)$")   # the name in its team color (#3681, #3889)
MORE = 20                   # seconds after the first line of an answer in which more lines belong to it
LOAD = 8                    # seconds after the first join: the chunks load
DONE = ("ok", "yes")        # a one-word answer ends at once
CHEAT_WAIT = 30             # seconds that the guide waits for the game to do a cheat code (no --cheats: never)


def out(*a):
    print(*a, flush=True)


def server(port, root=None):
    """(folder, RCON port, password) of the newest server folder with game port `port`."""
    for d in sorted(glob.glob(os.path.join(root or mc_check.workdir(), "tmp*")), key=os.path.getmtime, reverse=True):
        p = os.path.join(d, "server.properties")
        if os.path.exists(p):
            with open(p) as f:
                props = dict(ln.strip().split("=", 1) for ln in f if "=" in ln)
            if props.get("server-port") == str(port):
                return d, int(props["rcon.port"]), props["rcon.password"]
    sys.exit(f"no server with port {port} in {root or mc_check.workdir()}")


def names(objects):
    """{"{NAMEn}": UUID} of the first object of each name and player, and "{NAME}" for player 1."""
    got = {}
    for o in objects:
        if o.get("kind") == "building" and "footprint" in o:
            uuid = combat.target_uuid(o["footprint"])
        elif o.get("uuid"):
            uuid = o["uuid"]
        else:
            continue
        got.setdefault(f"{{{o['name']}{o['player']}}}", uuid)
        if o["player"] == 1:
            got.setdefault(f"{{{o['name']}}}", uuid)
    return got


def fill(cmd, values):
    """cmd with each placeholder of values replaced. An unknown placeholder stays: the server says what is wrong."""
    return re.sub(r"\{\w+\}", lambda m: values.get(m.group(0), m.group(0)), cmd)


class Guide:
    """The steps of one play test. command: sends one server command (RCON) and returns the reply; log: the path of
    the server log."""

    def __init__(self, command, log, steps, values, clock=time.monotonic, sleep=time.sleep, say_log=out):
        self.command, self.log, self.steps, self.values = command, log, steps, values
        self.clock, self.sleep, self.out = clock, sleep, say_log
        self.seen, self.answers = 0, []
        bad = sorted({c for s in steps for c in s.get("cheats", [])} - set(cheats.NAMES))
        if bad:
            raise ValueError(f"unknown cheat codes: {', '.join(bad)} (game/cheats.py NAMES)")

    def say(self, msg, color="gold"):
        self.command(f"tellraw @a {json.dumps([{'text': '[check] ', 'color': 'aqua'}, {'text': msg, 'color': color}])}")

    def players(self):
        return [p.strip() for p in self.command("list").split(":", 1)[-1].split(",") if p.strip()]

    def cheat(self, player, code):
        """Run cheat code for player: set its score as the plugin does, then wait until cheats.clicks resets it."""
        self.command(f"scoreboard players set {player} {cheats.OBJECTIVE} {cheats.NAMES.index(code) + 1}")
        end = self.clock() + CHEAT_WAIT
        while re.search(r" has \d+ ", self.command(f"scoreboard players get {player} {cheats.OBJECTIVE}")):
            if self.clock() > end:
                return self.out(f"CHEAT {code} -> not done in {CHEAT_WAIT} s: start game/run.py with --cheats")
            self.sleep(0.5)
        self.out(f"CHEAT {code} -> done")

    def chat(self):
        """The new chat lines of players since the last call: [(name, text)]."""
        try:
            with open(self.log, errors="replace") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            return []
        if len(lines) < self.seen:                                  # a new log (a restart, #979)
            self.seen = 0
        new, self.seen = lines[self.seen:], len(lines)
        return [m.groups() for ln in new if (m := CHAT.search(ln))]

    def answer(self):
        """The next answer: (player, text). Lines in MORE seconds after the first one belong to it."""
        while not (got := self.chat()):
            self.sleep(0.5)
        who, parts = got[0][0], [t for _, t in got]
        end = self.clock() + MORE
        while not (len(parts) == 1 and parts[0].strip().lower() in DONE) and self.clock() < end:
            self.sleep(0.5)
            parts += [t for _, t in self.chat()]
        return who, " ".join(p.strip() for p in parts)

    def run(self):
        while not self.players():
            self.sleep(1)
        self.out(f"JOINED {self.players()}")
        self.sleep(LOAD)
        self.chat()                                                 # only answers after a question count
        for k, s in enumerate(self.steps, 1):
            for c in s.get("setup", []):
                c = fill(c, self.values)
                self.out(f"SETUP {c} -> {self.command(c).strip()[:120]}")
            for c in s.get("cheats", []):
                self.cheat(self.players()[0], c)
            self.say(f"Step {k} of {len(self.steps)}: {s['task']}")
            self.say(s["ask"], "yellow")
            self.say("When you are done, type your answer in the chat: ok, or what is wrong.", "gray")
            self.out(f"ASK {s['name']}")
            self.chat()
            who, text = self.answer()
            self.answers.append({"step": s["name"], "player": who, "text": text})
            self.out(f"ANSWER {s['name']}: <{who}> {text}")
            self.say("Thank you." + (" Next step in 3 seconds." if k < len(self.steps) else " This part is done."),
                     "green")
            yield self.answers
            self.sleep(3)
        self.out(f"DONE {len(self.answers)} answers")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", type=int, help="the game port of the running server")
    ap.add_argument("world")
    ap.add_argument("steps", help="JSON list of steps")
    ap.add_argument("--out", default="play.json", help="the answers (JSON, default play.json)")
    a = ap.parse_args(argv)
    folder, rport, password = server(a.port)
    r = Rcon("127.0.0.1", rport, password)
    with open(os.path.join(a.world, "aoe2mc.json")) as f:
        values = names(json.load(f)["objects"])
    with open(a.steps) as f:
        steps = json.load(f)
    guide = Guide(r.command, os.path.join(folder, "logs", "latest.log"), steps, values)
    for answers in guide.run():                                     # write after each answer: a stop keeps them
        with open(a.out, "w") as f:
            json.dump(answers, f, indent=1)


if __name__ == "__main__":
    main()
