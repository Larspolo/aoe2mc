#!/usr/bin/env python3
"""
The game program: start a Paper server on a converted world, with RCON on localhost, and send commands to it.

Usage:
    python3 game/run.py WORLD [--version 26.3]    # type commands (without "/"); Ctrl-C stops the server
    python3 game/run.py WORLD --server vanilla    # the vanilla server of Mojang instead of Paper
    python3 game/run.py WORLD --bench 1000        # measure the commands per second through RCON, then stop
    python3 game/run.py WORLD --play              # villagers gather wood, food, gold, stone (game/gather.py); Ctrl-C stops
    python3 game/run.py WORLD --play --cheats     # also the AoE2 cheat codes in the chat (game/cheats.py)
    python3 game/run.py WORLD --play --bot        # also a bot plays player 2: its villagers gather (game/bot.py)
    python3 game/run.py WORLD --play --log F.jsonl  # also write a timed event log (tools/measure_gather.py reads it)
    python3 game/run.py WORLD --replay [--speed 4]  # replay the recorded game of the world (game/replay.py), then stop

Join with Minecraft (multiplayer, localhost): players play in creative mode and get operator rights.
The server plays the world in place (the game changes it). Server files (eula, properties, logs) go to .cache/.
Platform choice: docs/research/gameplay.md (#135). Paper (#433, #434) adds path finding through a plugin;
converted worlds stay vanilla, and tools/mc_check.py checks them with the vanilla server.
"""
import argparse
import contextlib
import glob
import hashlib
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
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "tools")]
import mc_check  # noqa: E402
from rcon import Rcon  # noqa: E402

JOINED = re.compile(r"[/ ]INFO\]: (\w{1,16}) joined the game$")   # a chat line starts with "<name>", not with a name
PAPER = os.path.join(os.path.dirname(mc_check.CACHE), "paper")       # ~/.cache/aoe2mc/paper/VERSION/
FILL = "https://fill.papermc.io/v3/projects/paper/versions"
AGENT = {"User-Agent": "aoe2mc (https://github.com/Larspolo/aoe2mc)"}   # the Paper API refuses Python-urllib (403)


PLUGIN = os.path.join(HERE, "plugin")                               # the Paper plugin: aoe moveto, aoe attack (#435)


def plugin_jar(version):
    """The jar of game/plugin: built with the Gradle wrapper when its source changed (the name has its hash).
    Gradle needs a JDK of the server's Java version (javac): openjdk-25-jdk-headless for 26.3."""
    files = [os.path.join(PLUGIN, f) for f in ("build.gradle.kts", "settings.gradle.kts",
                                               "gradle/wrapper/gradle-wrapper.properties")]
    files += sorted(glob.glob(os.path.join(PLUGIN, "src", "**", "*.*"), recursive=True))
    h = hashlib.sha256()
    for f in files:
        h.update(os.path.relpath(f, PLUGIN).encode() + b"\0" + open(f, "rb").read())
    path = os.path.join(os.path.dirname(mc_check.CACHE), "plugin", f"aoe2mc-{h.hexdigest()[:16]}.jar")
    if not os.path.exists(path):
        build_plugin(version, path)
    return path


def build_plugin(version, path):
    jdk = os.path.dirname(os.path.dirname(os.path.realpath(mc_check.java_for(version))))
    if not os.path.exists(os.path.join(jdk, "bin", "javac")):
        sys.exit(f"no javac in {jdk}: install the JDK (apt-get install openjdk-25-jdk-headless)")
    subprocess.run([os.path.join(PLUGIN, "gradlew"), "--no-daemon", "-q", "jar"], cwd=PLUGIN, check=True,
                   env={**os.environ, "JAVA_HOME": jdk})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copy(os.path.join(PLUGIN, "build", "libs", "aoe2mc-plugin.jar"), path + ".part")
    os.replace(path + ".part", path)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=300) as r:
        return r.read()


def paper_jar(version):
    """The Paper server jar for the Minecraft version: the cached one, else the latest build of the downloads API.
    The jar comes from fill-data.papermc.io (#439). Delete the folder to get a newer build."""
    folder = os.path.join(PAPER, version)
    jars = sorted(glob.glob(os.path.join(folder, "paper-*.jar")), key=os.path.getmtime)
    if jars:
        return jars[-1]
    try:
        build = json.loads(get(f"{FILL}/{version}/builds/latest"))
    except OSError as e:
        sys.exit(f"no Paper build for Minecraft {version} ({e}); use --server vanilla")
    jar = build["downloads"]["server:default"]
    data = get(jar["url"])
    if hashlib.sha256(data).hexdigest() != jar["checksums"]["sha256"]:
        sys.exit(f"bad checksum: {jar['url']}")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, jar["name"])
    with open(path + ".part", "wb") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return path


# Paper (Spigot) ticks a unit far from all players only now and then: such a villager does not walk (#437). Vanilla
# has no such range, and the units of a game must move where no player is: 0 turns the range off.
SPIGOT = "world-settings:\n  default:\n    entity-activation-range:\n" + "".join(
    f"      {k}: 0\n" for k in ("animals", "monsters", "raiders", "misc", "water", "villagers", "flying-monsters"))


def properties(game_port, rcon_port, password):
    """server.properties: only local players can join (127.0.0.1). They play in creative mode (#292).
    A missing white-list becomes "true" in 26.3: then no player can join (#285)."""
    return (f"online-mode=false\nserver-ip=127.0.0.1\nserver-port={game_port}\nwhite-list=false\n"
            f"enable-rcon=true\nrcon.port={rcon_port}\nrcon.password={password}\n"
            "spawn-protection=0\nmax-tick-time=-1\nenable-query=false\nbroadcast-rcon-to-ops=false\n"
            "gamemode=creative\nforce-gamemode=true\n")


class Game:
    """A running server with an RCON connection. Use it in a `with` block, so that the server always stops."""

    def __init__(self, world, version=mc_check.DEFAULT_VERSION, timeout=300, server="paper"):
        self.world, self.version, self.timeout, self.kind = os.path.abspath(world), version, timeout, server
        self.server = self.rcon = None
        self.lock, self.seen = threading.Lock(), 0     # the op thread and the game send commands

    def start(self):
        java, jvm, plugins = mc_check.java_for(self.version), [], []
        if self.kind == "paper":                     # Paper patches the Mojang jar once, into the cache
            jar, plugins = paper_jar(self.version), [plugin_jar(self.version)]
            jvm = [f"-DbundlerRepoDir={os.path.dirname(jar)}"]
        else:
            jar = mc_check.server_jar(self.version)
        # Paper writes usercache.json into the folder of the world folder: remove it after the game
        cache = os.path.join(os.path.dirname(self.world), "usercache.json")
        self.usercache = None if os.path.exists(cache) else cache
        self.folder = tempfile.mkdtemp(dir=mc_check.workdir())
        self.port, self.game_port, password = mc_check.free_port(), mc_check.free_port(), secrets.token_hex(16)
        with open(os.path.join(self.folder, "eula.txt"), "w") as f:
            f.write("eula=true\n")
        for p in plugins:
            os.makedirs(os.path.join(self.folder, "plugins"), exist_ok=True)
            shutil.copy(p, os.path.join(self.folder, "plugins", "aoe2mc-plugin.jar"))
        with open(os.path.join(self.folder, "server.properties"), "w") as f:
            f.write(properties(self.game_port, self.port, password))
        if self.kind == "paper":
            with open(os.path.join(self.folder, "spigot.yml"), "w") as f:
                f.write(SPIGOT)
        # --universe and --world: the server uses the world folder where it is, not a copy
        self.server = mc_check.Server(java, jar, self.folder, ["--universe", os.path.dirname(self.world),
                                                               "--world", os.path.basename(self.world)], jvm)
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
        if getattr(self, "usercache", None) and os.path.exists(self.usercache):
            os.remove(self.usercache)

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


def play(game, world, log=None, cheats=False, bot=False, seconds=None):
    import gather
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    game.forceload()
    for _ in range(60):                              # entities load in other threads
        g = gather.Gather(game, data, log=log, cheats=cheats).setup()
        if len(g.villagers) == len(g.units):
            break
        time.sleep(1)
    if bot:
        import bot as bots
        g.bots = [bots.Bot(game, data, share=g, log=log).setup()]
        print(f"A bot plays player 2: {len(g.bots[0].g.villagers)} villagers gather.", file=sys.stderr)
    import combat
    combat.setup(game, data)                         # AoE2 hit points and damage (#514)
    print(f"Join the server localhost:{game.game_port} (Minecraft {game.version}, multiplayer, direct connection).\n"
          f"{len(g.villagers)} villagers of player 1. Hold the carrot on a stick: right click a villager to select it,\n"
          "then right click a tree, a fruit bush or a mine. To build: /trigger aoe_build set N (the menu is in the chat),\n"
          "then right click the ground. Right click your town center to train a villager (50 food). Ctrl-C stops.", file=sys.stderr)
    g.run(seconds)
    return g


def replay(game, world, speed=1.0, start="0:00"):
    import replay
    start = replay.aoe2mc.game_time(start)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    if "timeline" not in data:
        sys.exit("--replay needs a world of a recorded game (.aoe2record)")
    game.forceload()
    if game.kind == "paper":                         # the start units and buildings fight with AoE2 values (#632)
        import combat
        combat.setup(game, data)
    import replay_input
    control = replay_input.Input(game)              # hotbar items, menu and /trigger aoe_replay (#688)
    control.setup()
    print(f"Join the server localhost:{game.game_port} (Minecraft {game.version}). The replay starts now "
          f"at speed {speed}. Right click the items in your hotbar, or /trigger aoe_replay set N.", file=sys.stderr)
    stats = replay.Replay(game, data, game.version, ai=game.kind == "paper").run(speed, start, bar=True, poll=control)
    print(f"{stats['events']} events, {stats['commands']} commands in {stats['busy']} s "
          f"({stats['rate']} commands per second, the timeline needs {stats['need']}), largest lag {stats['lag']} s")
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("--version", default=mc_check.DEFAULT_VERSION, help="Minecraft version of the world")
    ap.add_argument("--server", choices=["paper", "vanilla"], default="paper", help="server program (default: Paper)")
    ap.add_argument("--bench", type=int, metavar="N", help="send N commands, print the commands per second, stop")
    ap.add_argument("--play", action="store_true", help="play: villagers of player 1 gather resources (aoe2mc.json)")
    ap.add_argument("--replay", action="store_true", help="replay the timeline of a recorded game (aoe2mc.json)")
    ap.add_argument("--speed", type=float, default=1.0, help="--replay: times the game speed (default 1)")
    ap.add_argument("--from", dest="start", default="0:00", metavar="MM:SS", help="--replay: start at this game time")
    ap.add_argument("--cheats", action="store_true", help="--play: the AoE2 cheat codes in the chat (off as in AoE2)")
    ap.add_argument("--bot", action="store_true", help="--play: a bot plays player 2 (game/bot.py)")
    ap.add_argument("--log", metavar="FILE", help="--play: write one JSON line per villager event (time, state, load)")
    a = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    game = Game(a.world, a.version, server=a.server)
    try:
        game.start()
        print(f"Server is ready. RCON on 127.0.0.1:{game.port}. Ctrl-C stops the server.", file=sys.stderr)
        if a.bench:
            print(f"{bench(game, a.bench):.0f} commands per second through RCON")
            return
        if a.replay:
            replay(game, a.world, a.speed, a.start)
            return
        if a.play:
            with open(a.log, "w") if a.log else contextlib.nullcontext() as log:
                play(game, a.world, log, a.cheats, a.bot)
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
