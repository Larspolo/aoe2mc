#!/usr/bin/env python3
"""
Join a --host game with real clients (#5916, the check of docs/PLAYTEST.md section 3, "Play with friends"): level 4
of the verify skill for --host, --invite and --offline (game/run.py).

Usage:
    python3 aoe2mc.py --random-map arabia --seed 1 --resource-pack OUTWorld
    python3 tools/host_check.py OUTWorld OUTDIR [--speed 4] [--beat N]

The tool copies the world and runs `run.main([WORLD, --play, --host, --invite alice,bob, --offline, --people 2])`
(the clients of tools/mc_shot.py have no Minecraft login). Client "alice" (the host) joins on localhost. Client "bob"
joins on ADDRESS:PORT of the line "Join the server ADDRESS:PORT (other computers on the network)." and loads the pack
from the PackServer of the network address. The tool sets both people "Ready" (as tools/rejoin_check.py). Then
client "eve" (not invited) tries to join: the server log must show the white-list refusal. Then the tool types
`whitelist add eve` in the console of the game program (stdin, #5924) and eve joins again. OUTDIR gets result.json.
Exit 0: all points are OK.
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

import mc_shot  # noqa: E402
import rejoin_check  # noqa: E402
import run  # noqa: E402

A, B, E = "alice", "bob", "eve"
LINE = re.compile(r"Join the server (\S+):(\d+) \(other computers on the network\)\.")
STOP_REFUSED = re.compile(r"Unknown or incomplete command|permission", re.I)
REFUSED = re.compile(rf"\b{E}\b.*white-?list|white-?list.*\b{E}\b", re.I)


class Tee:
    """sys.stderr that also keeps the lines: the tool reads the printed address line."""

    def __init__(self, f):
        self.f, self.lines = f, []

    def write(self, s):
        self.lines += s.splitlines()
        return self.f.write(s)

    def __getattr__(self, k):
        return getattr(self.f, k)


class Client(mc_shot.Client):
    """mc_shot.Client that keeps its log in OUT/<name>.log: the log of a failed join shows the cause."""

    out = None

    def __exit__(self, *exc):
        if self.out and self.log:
            self.log.flush()
            shutil.copy(self.log_path, os.path.join(self.out, f"{self.name}.log"))
        return super().__exit__(*exc)


def result(line, port, pack_url, pack_gets, team, refused, eve_on, errors, ops, invited):
    """{point: (ok, detail)} of the check. line: the (ADDRESS, PORT) of the printed line or None; pack_gets: the
    client addresses of the pack downloads; refused: the server log lines of the refusal of eve; ops: (the server
    still runs after the /stop of bob, the chat lines of bob after /stop, after /controls); invited: eve is online
    after the whitelist add."""
    addr = line[0] if line else None
    out = {"the address line": (bool(line) and addr not in ("localhost", "127.0.0.1") and line[1] == str(port),
                                f"{line} (game port {port})"),
           "the pack URL is on the network address": (bool(addr) and f"//{addr}:" in (pack_url or ""), pack_url),
           "bob loads the pack on the network address": (addr in pack_gets, f"downloads from {sorted(set(pack_gets))}"),
           "bob plays player 2": ("passed" in team, team),
           "bob cannot /stop the server": (ops[0] and any(STOP_REFUSED.search(x) for x in ops[1]),
                                           f"server {'up' if ops[0] else 'stopped'}; " + "; ".join(ops[1][:2])),
           "bob gets /controls": (bool(ops[2]), "; ".join(ops[2][:3])),
           "eve cannot join": (bool(refused) and not eve_on, "; ".join(refused[:2]) or f"no refusal, online {eve_on}"),
           "eve joins after whitelist add in the console": (invited, f"online {invited}"),
           "no server errors": (not errors, "; ".join(e[:200] for e in errors[:5]))}
    return {k: (bool(ok), d) for k, (ok, d) in out.items()}


def drive(games, a, report, tee):
    try:
        while not games or not getattr(games[0], "game_port", None):
            time.sleep(1)
        game = games[0]
        while True:
            try:
                game.command("list")
                break
            except Exception:
                time.sleep(2)
        gets = []
        if game.pack and hasattr(game.pack, "http"):                    # record the address of each download
            h = game.pack.http.RequestHandlerClass
            get = h.do_GET
            h.do_GET = lambda s: (gets.append(s.client_address[0]), get(s))[1]
        online = lambda n: n in game.command("list").split(":", 1)[-1]     # noqa: E731
        t = time.time()
        while not any(LINE.search(x) for x in tee.lines) and time.time() - t < 300:
            time.sleep(1)
        m = next((LINE.search(x) for x in tee.lines if LINE.search(x)), None)
        line = m.groups() if m else None
        with Client(game.game_port, game.version, name=A, world=a.copy, host="localhost") as ca:
            ca.wait_join(lambda: online(A))
            with Client(game.game_port, game.version, name=B, world=a.copy, chat=True,
                                host=line[0] if line else "127.0.0.1") as cb:
                cb.wait_join(lambda: online(B))
                while not getattr(game, "wait", False):
                    time.sleep(0.5)
                while game.wait:
                    game.ready = set(game.joined)                          # the "Ready" click of the lobby page
                    time.sleep(0.5)
                time.sleep(3)
                team = game.command(f"execute if entity @a[name={B},team=p2]")
                cb.wait_loaded(game)
                said = []
                for c in ("/stop", "/controls"):                           # a friend has op level 2 (#5925)
                    before = len(rejoin_check.chat_of(cb))
                    cb.key("t")
                    time.sleep(1)
                    cb.xdo("type", "--delay", "50", c)
                    cb.key("Return")
                    time.sleep(4)
                    said.append(rejoin_check.chat_of(cb)[before:])
                try:
                    up = online(B)
                except Exception:                                          # the /stop of bob stopped the server
                    up = False
                ops = (up, *said)
                with Client(game.game_port, game.version, name=E, world=a.copy,
                                    host=line[0] if line else "127.0.0.1") as ce:
                    t, refused, eve_on = time.time(), [], False
                    while not refused and time.time() - t < 180 and ce.client.poll() is None:
                        refused = [x for x in game.server.log if REFUSED.search(x)]
                        eve_on = eve_on or online(E)
                        time.sleep(1)
                    time.sleep(3)
                    refused = [x for x in game.server.log if REFUSED.search(x)]
                    eve_on = eve_on or online(E)
                os.write(a.stdin, b"whitelist add eve\n")                 # the host types it (run.console)
                time.sleep(3)
                with Client(game.game_port, game.version, name=E, world=a.copy,
                                    host=line[0] if line else "127.0.0.1") as ce:
                    t, invited = time.time(), False
                    while not invited and time.time() - t < 180 and ce.client.poll() is None:
                        invited = online(E)
                        time.sleep(1)
        log = game.server.log
        errors = [x for x in log if rejoin_check.ERROR.search(x) and not rejoin_check.OFFLINE.search(x)]
        report.update(result(line, game.game_port, getattr(game.pack, "url", None), gets, team, refused, eve_on,
                             errors, ops, invited))
    except Exception:
        traceback.print_exc()
    finally:
        try:
            games[0].stop()
        finally:
            rejoin_check.done(report, a.out)


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("out", help="the folder of result.json")
    ap.add_argument("--speed", type=float, default=4.0, help="times the Normal game speed (default 4)")
    ap.add_argument("--beat", type=int, metavar="N", help="beat the claim of ticket N every 10 minutes")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse(argv)
    if a.beat:
        mc_shot.beat(a.beat)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    if not os.path.isfile(os.path.join(a.world, "resourcepacks", "resources.zip")):
        sys.exit(f"no resource pack in {a.world}: convert with --resource-pack (the check loads the pack)")
    os.makedirs(a.out, exist_ok=True)
    Client.out = a.out
    a.copy = os.path.join(tempfile.mkdtemp(), os.path.basename(os.path.normpath(a.world)))
    shutil.copytree(a.world, a.copy)                                   # the game changes the world
    games, report, init = [], {}, run.Game.__init__

    def game_init(self, *args, **kw):
        init(self, *args, **kw)
        games.append(self)

    run.Game.__init__ = game_init
    tee = sys.stderr = Tee(sys.stderr)
    r, a.stdin = os.pipe()                                             # run.console reads stdin: no EOF
    threading.Thread(target=drive, args=(games, a, report, tee), daemon=True).start()
    os.dup2(r, sys.stdin.fileno())
    run.main([a.copy, "--play", "--host", "--invite", f"{A},{B}", "--offline", "--people", "2",
              "--speed", f"{a.speed:g}"])
    rejoin_check.done(report, a.out)


if __name__ == "__main__":
    main()
