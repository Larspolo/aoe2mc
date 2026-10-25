#!/usr/bin/env python3
"""
The game program: start a vanilla server on a converted world, with RCON on localhost, and send commands to it.

Usage:
    python3 game/run.py WORLD [--version 26.3]    # type commands (without "/"); Ctrl-C stops the server
    python3 game/run.py WORLD --bench 1000        # measure the commands per second through RCON, then stop
    python3 game/run.py WORLD --play              # villagers gather wood (game/gather.py); Ctrl-C stops
    python3 game/run.py WORLD --play --log F.jsonl  # also write a timed event log (tools/measure_gather.py reads it)

Join with Minecraft (multiplayer, localhost): players play in creative mode and get operator rights.
The server plays the world in place (the game changes it). Server files (eula, properties, logs) go to .cache/.
Platform choice: docs/research/gameplay.md (#135).
"""
import argparse
import contextlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "tools")]
import mc_check  # noqa: E402
from rcon import Rcon  # noqa: E402

JOINED = re.compile(r"/INFO\]: (\w{1,16}) joined the game$")      # a chat line starts with "<name>", not with a name


def properties(game_port, rcon_port, password):
    """server.properties: only local players can join (127.0.0.1). They play in creative mode (#292)."""
    return (f"online-mode=false\nserver-ip=127.0.0.1\nserver-port={game_port}\n"
            f"enable-rcon=true\nrcon.port={rcon_port}\nrcon.password={password}\n"
            "spawn-protection=0\nmax-tick-time=-1\nenable-query=false\nbroadcast-rcon-to-ops=false\n"
            "gamemode=creative\nforce-gamemode=true\n")


class Game:
    """A running server with an RCON connection. Use it in a `with` block, so that the server always stops."""

    def __init__(self, world, version=mc_check.DEFAULT_VERSION, timeout=300):
        self.world, self.version, self.timeout = os.path.abspath(world), version, timeout
        self.server = self.rcon = None
        self.lock, self.seen = threading.Lock(), 0     # the op thread and the game send commands

    def start(self):
        jar, java = mc_check.server_jar(self.version), mc_check.java_for(self.version)
        self.folder = tempfile.mkdtemp(dir=mc_check.workdir())
        self.port, self.game_port, password = mc_check.free_port(), mc_check.free_port(), secrets.token_hex(16)
        with open(os.path.join(self.folder, "eula.txt"), "w") as f:
            f.write("eula=true\n")
        with open(os.path.join(self.folder, "server.properties"), "w") as f:
            f.write(properties(self.game_port, self.port, password))
        # --universe and --world: the server uses the world folder where it is, not a copy
        self.server = mc_check.Server(java, jar, self.folder, ["--universe", os.path.dirname(self.world),
                                                               "--world", os.path.basename(self.world)])
        try:
            self.server.wait(r"\]: Done \(", self.timeout)
            self.rcon = Rcon("127.0.0.1", self.port, password)
        except BaseException:
            self.stop()
            raise
        threading.Thread(target=self._op_loop, daemon=True).start()
        return self

    def command(self, cmd):
        with self.lock:
            return self.rcon.command(cmd)

    def op_joined(self):
        """Give operator rights to each player who joined since the last call (/gamemode, /tp without RCON, #292).
        The server listens only on 127.0.0.1, so only local players can join."""
        log = self.server.log
        new, self.seen = log[self.seen:], len(log)
        for line in new:
            if m := JOINED.search(line):
                self.command(f"op {m.group(1)}")

    def _op_loop(self):
        try:
            while self.rcon:
                self.op_joined()
                time.sleep(0.5)
        except (OSError, AttributeError):         # the server stops
            pass

    def forceload(self):
        """Load all chunks of the world, so that all units (entities) are there."""
        x0, z0, x1, z1 = mc_check.chunks(self.world)
        for cx in range(x0, x1 + 1, 16):             # forceload takes at most 256 chunks per command
            for cz in range(z0, z1 + 1, 16):
                self.command(f"forceload add {cx * 16} {cz * 16} {min(cx + 15, x1) * 16} {min(cz + 15, z1) * 16}")

    def stop(self):
        if self.rcon:
            self.rcon.close()
            self.rcon = None
        if self.server and self.server.p.poll() is None:
            try:                                     # Ctrl-C reaches the server too: it can stop by itself
                self.server.send("stop")
                self.server.p.wait(self.timeout)
            except (OSError, subprocess.TimeoutExpired):
                self.server.p.kill()
                self.server.p.wait()
        if getattr(self, "folder", None):
            shutil.rmtree(self.folder, ignore_errors=True)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def bench(game, n=1000):
    """Commands per second through RCON (one command, one answer, in sequence)."""
    t = time.perf_counter()
    for _ in range(n):
        game.command("time query gametime")
    return n / (time.perf_counter() - t)


def play(game, world, log=None):
    import gather
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    game.forceload()
    for _ in range(60):                              # entities load in other threads
        g = gather.Gather(game, data, log=log).setup()
        if len(g.villagers) == len(g.units):
            break
        time.sleep(1)
    print(f"Join the server localhost:{game.game_port} (Minecraft {game.version}, multiplayer, direct connection).\n"
          f"{len(g.villagers)} villagers of player 1. Hold the carrot on a stick: right click a villager to select it,\n"
          "then right click a tree. Ctrl-C stops.", file=sys.stderr)
    g.run()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("--version", default=mc_check.DEFAULT_VERSION, help="Minecraft version of the world")
    ap.add_argument("--bench", type=int, metavar="N", help="send N commands, print the commands per second, stop")
    ap.add_argument("--play", action="store_true", help="play: villagers of player 1 gather wood (aoe2mc.json)")
    ap.add_argument("--log", metavar="FILE", help="--play: write one JSON line per villager event (time, state, load)")
    a = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    game = Game(a.world, a.version)
    try:
        game.start()
        print(f"Server is ready. RCON on 127.0.0.1:{game.port}. Ctrl-C stops the server.", file=sys.stderr)
        if a.bench:
            print(f"{bench(game, a.bench):.0f} commands per second through RCON")
            return
        if a.play:
            with open(a.log, "w") if a.log else contextlib.nullcontext() as log:
                play(game, a.world, log)
            return
        while True:
            line = input("> ").strip().lstrip("/")
            if line:
                print(game.command(line))
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print("Stopping the server ...", file=sys.stderr)
        game.stop()


if __name__ == "__main__":
    main()
