#!/usr/bin/env python3
"""
The watcher of an owner demo (the `demo` skill): it follows a running `game/run.py --play` game, prints what the agent
must handle and stops, so that the session uses no model turn while nothing happens.

Usage:
    python3 game/demo_watch.py GAME_PORT [--out out/demo] [--game out/demo/game.log] [--quiet 20] [--hours 6]
    python3 game/demo_watch.py GAME_PORT --say TEXT      # say TEXT in the chat of all players, then stop
                                                         # (each #N is a link to issue N of the repository)

GAME_PORT: the port of "Join the server localhost:PORT" (play_guide.server finds the server folder of that port).
--game: the output of game/run.py (stdout and stderr: `python3 -u game/run.py ... 2>&1 | tee -i out/demo/game.log`).
It prints one line per event:
    CHAT <name> text   a chat line of a player (the lines of the next QUIET seconds come in the same call)
    ERROR line         a server log line with ERROR, an exception, or a warning of the plugin [aoe2mc]
    CRASH line         the last line of a Python traceback in the output of game/run.py
    SHOT path          a new Minecraft screenshot (F2) in --shots
    STOP               the server stopped
It stops QUIET seconds after the last event, at once after STOP, and with exit code 1 after --hours without an event.
Game.stop deletes the server folder with its log: the watcher copies each server log line to OUT/server.log, so the
log of a crash stays. OUT/watch.json keeps what it reported, so the next call gives only the new events.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "framework", "tools"))
import agent_config  # noqa: E402
import play_guide  # noqa: E402
from rcon import Rcon  # noqa: E402

SHOTS = os.path.expanduser("~/Library/Application Support/minecraft/screenshots" if sys.platform == "darwin"
                           else "~/.minecraft/screenshots")
ERROR = re.compile(r"/ERROR\]|Exception|/WARN\]: \[aoe2mc\]")
QUIET = 20                  # seconds after the last event: more feedback lines come in the same call
ISSUE = re.compile(r"(#\d+)")


def chat(text, repo):
    """The tellraw text of a demo line: each #N is a link to issue N of repo (owner request in the demo of
    2026-10-27), so that the owner opens the ticket from the chat."""
    parts = [{"text": "[demo] ", "color": "aqua"}]
    for part in filter(None, ISSUE.split(text)):
        url = f"https://github.com/{repo}/issues/{part[1:]}"
        parts.append({"text": part, "color": "aqua", "underlined": True,
                      "click_event": {"action": "open_url", "url": url},
                      "hover_event": {"action": "show_text", "value": url}} if ISSUE.fullmatch(part)
                     else {"text": part, "color": "gold"})
    return parts


class Watch:
    """The new events of one game. folder: the server folder; out: the folder of server.log and watch.json;
    game: the output file of game/run.py (or None); shots: the screenshot folder of the Minecraft client."""

    def __init__(self, folder, out, game=None, shots=SHOTS):
        self.folder, self.out, self.game, self.shots = folder, out, game, shots
        self.path = os.path.join(out, "watch.json")
        try:
            with open(self.path) as f:
                self.state = json.load(f)
        except (FileNotFoundError, ValueError):
            self.state = {}
        if self.state.get("folder") != folder:      # a new game: old screenshots are not events
            self.state = {"folder": folder, "server": 0, "game": self.state.get("game", 0), "tb": False,
                          "stopped": False, "shots": sorted(os.path.basename(p) for p in self.pngs())}
            self.copy([f"--- server {folder} ---"])

    def pngs(self):
        return glob.glob(os.path.join(self.shots, "*.png"))

    def copy(self, lines):
        with open(os.path.join(self.out, "server.log"), "a") as f:
            f.write("".join(ln + "\n" for ln in lines))

    def lines(self, key, path):
        """The new complete lines of the file path since the last call (all again when the file is new: a restart)."""
        try:
            with open(path, errors="replace") as f:
                lines = f.read().split("\n")[:-1]           # the last part has no newline yet: read it next time
        except (FileNotFoundError, TypeError):
            return []
        seen = self.state[key] if len(lines) >= self.state[key] else 0
        self.state[key] = len(lines)
        return lines[seen:]

    def poll(self):
        """The events since the last call: [(kind, text)]."""
        ev, server = [], self.lines("server", os.path.join(self.folder, "logs", "latest.log"))
        self.copy(server)
        for ln in server:
            if m := play_guide.CHAT.search(ln):
                ev.append(("CHAT", f"<{m[1]}> {m[2]}"))
            elif ERROR.search(ln):
                ev.append(("ERROR", ln))
            elif "Stopping server" in ln:
                ev.append(("STOP", ""))
        for ln in self.lines("game", self.game):
            if ln.startswith("Traceback"):
                self.state["tb"] = True
            elif self.state["tb"] and not ln.startswith(" "):
                ev.append(("CRASH", ln))
                self.state["tb"] = False
        for p in sorted(self.pngs()):
            if (name := os.path.basename(p)) not in self.state["shots"]:
                self.state["shots"].append(name)
                ev.append(("SHOT", p))
        if not os.path.isdir(self.folder):          # Game.stop deleted it
            ev.append(("STOP", ""))
        if self.state["stopped"]:
            ev = [e for e in ev if e[0] != "STOP"]
        self.state["stopped"] |= any(k == "STOP" for k, _ in ev)
        with open(self.path, "w") as f:
            json.dump(self.state, f)
        return ev

    def run(self, quiet=QUIET, hours=6, clock=time.monotonic, sleep=time.sleep, out=print):
        """Print the events. Returns 0 quiet seconds after the last one (at once after STOP), 1 after hours with none."""
        end, last = clock() + hours * 3600, None
        while True:
            ev = self.poll()
            for kind, text in ev:
                out(f"{kind} {text}".rstrip(), flush=True)
            if any(k == "STOP" for k, _ in ev) or self.state["stopped"]:
                return 0
            last = clock() if ev else last
            if last is not None and clock() - last >= quiet:
                return 0
            if last is None and clock() > end:
                out(f"No event in {hours:g} hours.", flush=True)
                return 1
            sleep(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("port", type=int, help='the port of "Join the server localhost:PORT"')
    ap.add_argument("--out", default="out/demo", help="the folder of server.log and watch.json")
    ap.add_argument("--game", help="the output file of game/run.py (stdout and stderr)")
    ap.add_argument("--shots", default=SHOTS, help="the screenshot folder of the Minecraft client")
    ap.add_argument("--quiet", type=float, default=QUIET, help="seconds after the last event before the stop")
    ap.add_argument("--hours", type=float, default=6, help="stop with exit code 1 after this time with no event")
    ap.add_argument("--say", metavar="TEXT", help="say TEXT in the chat of all players, then stop")
    a = ap.parse_args(argv)
    folder, rcon_port, password = play_guide.server(a.port)
    if a.say:
        with Rcon("127.0.0.1", rcon_port, password, retry=0) as r:
            r.command("tellraw @a " + json.dumps(chat(a.say, agent_config.load()["repo"])))
        return 0
    os.makedirs(a.out, exist_ok=True)
    return Watch(folder, a.out, a.game, a.shots).run(a.quiet, a.hours)


if __name__ == "__main__":
    sys.exit(main())
