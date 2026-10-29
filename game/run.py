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
    python3 game/run.py WORLD --play --bot --bot-attack 5:00   # its soldiers attack player 1 from 5:00 (default 10:00)
    python3 game/run.py WORLD --play --bot --ai-difficulty hard   # the AoE2 setting "AI difficulty" (#2661)
    python3 game/run.py WORLD --play --log F.jsonl  # also write a timed event log (tools/measure_gather.py reads it)
    python3 game/run.py WORLD --play --record F.jsonl  # Record Game: --replay --replay-file F.jsonl plays it (#2649)
    python3 game/run.py WORLD --play --bot --treaty 20:00   # the AoE2 setting "Treaty length": no attack before 20:00 (#2297)
    python3 game/run.py WORLD --play --reveal all  # no fog of war: also the enemy units out of sight show (game/fog.py)
    python3 game/run.py WORLD --play --reveal explored  # the whole map starts explored on the minimap (#2932)
    python3 game/run.py WORLD --play --speed 2     # twice the AoE2 Normal speed: /tick rate 40 and shorter steps (#2057)
    python3 game/run.py WORLD --play --resources high  # the AoE2 setting "Starting resources" (#2264)
    python3 game/run.py WORLD --play --age castle      # the AoE2 setting "Starting age" (#2265)
    python3 game/run.py WORLD --play --end-age castle  # the AoE2 setting "Ending age" (#2346)
    python3 game/run.py WORLD --play --all-techs       # the AoE2 setting "All Techs" (#2298)
    python3 game/run.py WORLD --play --full-tech-tree  # the AoE2 setting "Full Tech Tree" (#2354)
    python3 game/run.py WORLD --play --turbo           # the AoE2 setting "Turbo Mode" (#2359)
    python3 game/run.py WORLD --play --bot --teams 1,1 --shared-exploration off   # no sight of the ally (#2602)
    python3 game/run.py WORLD --play --victory conquest  # the AoE2 setting "Victory": no wonder or relic win (#2316)
    python3 game/run.py WORLD --play --victory time-limit --victory-value 300   # the highest score at 300 years (#2356)
    python3 game/run.py WORLD --play --victory king-of-the-hill   # hold the monument in the center (#2360)
    python3 game/run.py WORLD --play --mode regicide   # the AoE2 game mode "Regicide": each player has a King (#2347)
    python3 game/run.py WORLD --play --mode empire-wars   # the AoE2 game mode "Empire Wars": a town at work (#2408)
    python3 game/run.py WORLD --play --mode sudden-death   # the AoE2 game mode "Sudden Death": one town center (#2407)
    python3 game/run.py WORLD --play --mode battle-royale  # "Battle Royale": the Corruption takes the map (#2439)
    python3 game/run.py WORLD --play --mode capture-the-relic   # "Capture the Relic": the center relic wins (#2440)
    python3 game/run.py WORLD --play --mode death-match   # the AoE2 game mode "Death Match": large resources (#2438)
    python3 game/run.py WORLD --play --mode defend-the-wonder   # "Defend the Wonder": player 1 has a Wonder (#2441)
    python3 game/run.py WORLD --play --mode wonder-race   # "Wonder Race": no attacks, the first wonder wins (#2406)
    python3 game/run.py WORLD --play --mode capture-the-relic --regicide   # a King on top of the mode (also
                                                     # --sudden-death, --empire-wars: AoE2 "Advanced Settings", #2490)
    python3 game/run.py WORLD --play --civ 1=BRITONS --civ 2=FRANKS   # the civilization of each player (#2267)
    python3 game/run.py WORLD --play --teams 1,1,2,2   # the team of each player, - is no team (#2296)
    python3 game/run.py WORLD --play --load SAVE   # go on with a saved game: Ctrl-C of --play saves into saves/ (#2255)
    python3 game/run.py WORLD --replay [--speed 4] [--follow N] [--view N]  # replay the recorded game of the world (game/replay.py), then wait for Ctrl-C

Join with Minecraft (multiplayer, localhost): players play in creative mode and get operator rights.
The server plays the world in place (the game changes it). Server files (eula, properties, logs) go to .cache/.
Platform choice: docs/research/gameplay.md (#135). Paper (#433, #434) adds path finding through a plugin;
converted worlds stay vanilla, and tools/mc_check.py checks them with the vanilla server.
"""
import argparse
import contextlib
import glob
import hashlib
import importlib
import json
import math
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "tools")]
import mc_check  # noqa: E402
import rcon  # noqa: E402
import table  # noqa: E402
from rcon import Rcon  # noqa: E402

# A chat line starts with "<name>", not with a name. Paper 26.3 writes "System chat: " and color codes (#1310).
JOINED = re.compile(r"[/ ]INFO\]: (?:System chat: )?(?:\x1b\[[0-9;]*m)?(\w{1,16})(?:\x1b\[[0-9;]*m)? joined the game"
                    r"(?:\x1b\[0m)?$")                # Paper 26.3: the name in its own color (#3566)
PAPER = os.path.join(os.path.dirname(mc_check.CACHE), "paper")       # ~/.cache/aoe2mc/paper/VERSION/
FILL = "https://fill.papermc.io/v3/projects/paper/versions"
AGENT = {"User-Agent": "aoe2mc (https://github.com/Larspolo/aoe2mc)"}   # the Paper API refuses Python-urllib (403)


PLUGIN = os.path.join(HERE, "plugin")                               # the Paper plugin: aoe moveto, aoe attack (#435)
BUNDLED = os.path.join(PLUGIN, "aoe2mc-plugin.jar")                # the jar in an app bundle (#1778): no JDK needed
STOP_LINE = "\x03"                                                  # the Stop of the window on Windows (gui.STOP_LINE, #3003)


def plugin_jar(version):
    """The jar of game/plugin: built with the Gradle wrapper when its source changed (the name has its hash).
    Gradle needs a JDK of the server's Java version (javac): openjdk-25-jdk-headless for 26.3. An app bundle
    (sys.frozen) has no source: it brings the jar that the packaging workflow built."""
    if getattr(sys, "frozen", False):
        return BUNDLED
    files = [os.path.join(PLUGIN, f) for f in ("build.gradle.kts", "settings.gradle.kts",
                                               "gradle/wrapper/gradle-wrapper.properties")]
    files += sorted(glob.glob(os.path.join(PLUGIN, "src", "**", "*.*"), recursive=True))
    h = hashlib.sha256()
    for f in files:
        h.update(os.path.relpath(f, PLUGIN).encode() + b"\0" + open(f, "rb").read())
    path = os.path.join(os.path.dirname(mc_check.CACHE), "plugin", f"aoe2mc-{h.hexdigest()[:16]}.jar")
    if not os.path.exists(path):
        with build_lock(path):
            if not os.path.exists(path):       # another process built it while we waited for the lock (#3570)
                build_plugin(version, path)
    return path


@contextlib.contextmanager
def build_lock(path):
    """A file lock around the build: parallel workers (pytest -n) then build the jar once, not in each process."""
    try:
        import fcntl
    except ImportError:                        # no fcntl on Windows: no lock
        yield
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def java_home(java):
    """The home of the JDK of a java binary, from Java itself: on macOS /usr/bin/java is a stub, not a link (#1126)."""
    out = subprocess.run([java, "-XshowSettings:properties", "-version"], capture_output=True, text=True).stderr
    m = re.search(r"^\s*java\.home = (.+)$", out, re.M)
    return m.group(1).strip() if m else os.path.dirname(os.path.dirname(os.path.realpath(java)))


def build_plugin(version, path):
    jdk = java_home(mc_check.java_for(version))
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


PROMPT = "The units of aoe2mc need this resource pack: they get the look of AoE2."


def pack_file(world):
    """resourcepacks/resources.zip of the world (--resource-pack, #2738), or None."""
    path = os.path.join(world, "resourcepacks", "resources.zip")
    return path if os.path.isfile(path) else None


RELEASE = os.path.join(HERE, "release.json")                        # the tag and pack SHA-1 of a bundle (#2741)
RELEASE_URL = "https://github.com/Larspolo/aoe2mc/releases/download/{tag}/aoe2mc-resourcepack.zip"


class ReleasePack:
    """The resource pack of the GitHub release of the bundle (#2741): the players download it from there."""

    def __init__(self, url, sha1):
        self.url, self.sha1 = url, sha1

    def stop(self):
        pass


def pack_source(path):
    """The source of the world pack path for the players: the release link when the app bundle (sys.frozen) has
    RELEASE (the workflow bundles.yml writes it on a tag) and the world pack has the SHA-1 of the release pack; else
    the local PackServer (#2740). A world of another version has another pack: the client refuses a wrong SHA-1."""
    sha1 = hashlib.sha1(open(path, "rb").read()).hexdigest()
    release = json.load(open(RELEASE)) if getattr(sys, "frozen", False) and os.path.isfile(RELEASE) else {}
    if release.get("tag") and release.get("sha1") == sha1:
        return ReleasePack(RELEASE_URL.format(tag=release["tag"]), sha1)
    return PackServer(path)


class PackServer:
    """Serve only the resource pack of the world over HTTP on 127.0.0.1 (#2740): the Minecraft server does not host
    it, it sends only the URL and the SHA-1 to each player who joins."""

    def __init__(self, path):
        import http.server
        data = open(path, "rb").read()
        self.sha1 = hashlib.sha1(data).hexdigest()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(h):
                if h.path != "/resources.zip":
                    return h.send_error(404)
                h.send_response(200)
                h.send_header("Content-Type", "application/zip")
                h.send_header("Content-Length", str(len(data)))
                h.end_headers()
                h.wfile.write(data)

            def log_message(h, *args):
                pass

        self.http = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)   # port 0: a free port, no race
        self.url = f"http://127.0.0.1:{self.http.server_address[1]}/resources.zip"
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def stop(self):
        self.http.shutdown()
        self.http.server_close()


def properties(game_port, rcon_port, password, pack=None):
    """server.properties: only local players can join (127.0.0.1). They play in creative mode (#292).
    A missing white-list becomes "true" in 26.3: then no player can join (#285). Each player is an operator
    (op_joined): the output of RCON and console commands (the "fill" of a falling building) must not go to its chat (#1799).
    pack: the PackServer of the world (#2740) or its ReleasePack (#2741). The units have no vanilla look without it: the player must accept it."""
    extra = (f"resource-pack={pack.url}\nresource-pack-sha1={pack.sha1}\nrequire-resource-pack=true\n"
             f"resource-pack-prompt={json.dumps({'text': PROMPT})}\n") if pack else ""
    return extra + (f"online-mode=false\nserver-ip=127.0.0.1\nserver-port={game_port}\nwhite-list=false\n"
            f"enable-rcon=true\nrcon.port={rcon_port}\nrcon.password={password}\n"
            "spawn-protection=0\nmax-tick-time=-1\nenable-query=false\nbroadcast-rcon-to-ops=false\n"
            "broadcast-console-to-ops=false\n"
            "gamemode=creative\nforce-gamemode=true\n")


def batches(cmds, limit=rcon.MAX):
    """The commands that send cmds in this order: `aoe batch` commands of at most limit bytes, each command in them
    URL-encoded with "+" for a space (the plugin decodes it, #2761). A batch of one command, and a command that is too
    long for a batch, go as they are."""
    out, part, size = [], [], len("aoe batch")
    for c in [*cmds, None]:
        e = c and c.replace("%", "%25").replace("+", "%2B").replace(" ", "+")
        if part and (c is None or size + 1 + len(e.encode()) > limit):
            out.append(part[0][0] if len(part) == 1 else "aoe batch " + " ".join(x for _, x in part))
            part, size = [], len("aoe batch")
        if c is not None and size + 1 + len(e.encode()) > limit:
            out.append(c)
        elif c is not None:
            part.append((c, e))
            size += 1 + len(e.encode())
    return out


SPECTATORS = ('team add spec "Spectators"', "team modify spec color gray")   # the team of the spectators (#2898)
CHAT_HINT = "Chat: a normal line goes to all, /tm TEXT to your allies, /msg NAME TEXT to one person."   # #3555


class Game:
    """A running server with an RCON connection. Use it in a `with` block, so that the server always stops.
    people: the people of a game (`--people`); sides: Minecraft name -> AoE2 player (#1310)."""
    people = 1
    spectators = frozenset()                         # the Minecraft players without a side (#2898)
    joined = frozenset()                             # the Minecraft players who joined (start_on_join, #3314)
    starts, yaw = {}, 0.0                            # AoE2 player -> its start block, the spawn yaw (aoe2mc.json, #3347)
    placed = frozenset()                             # the Minecraft players who went to the start of their side
    seats = ()                                       # --seats: the AoE2 player of each person in the join order (#3489)

    def __init__(self, world, version=mc_check.DEFAULT_VERSION, timeout=300, server="paper"):
        self.world, self.version, self.timeout, self.kind = os.path.abspath(world), version, timeout, server
        self.server = self.rcon = None
        self.lock, self.seen = threading.Lock(), 0     # the op thread and the game send commands
        self.sides = {}
        import units                                 # a world with the resource pack: own armor and weapons (#2742, #2744)
        units.ASSETS = pack_file(self.world) is not None

    def start(self):
        java, jvm, plugins = mc_check.java_for(self.version), [], []
        if self.kind == "paper":                     # Paper patches the Mojang jar once, into the cache
            jar, plugins = paper_jar(self.version), [plugin_jar(self.version)]
            # the colors of the log (a chat name, #3681) also with no TERM, as on CI: Adventure reads TERM (#3889)
            jvm = [f"-DbundlerRepoDir={os.path.dirname(jar)}", "-Dnet.kyori.ansi.colorLevel=indexed16"]
        else:
            jar = mc_check.server_jar(self.version)
        # Paper writes usercache.json into the folder of the world folder: remove it after the game
        cache = os.path.join(os.path.dirname(self.world), "usercache.json")
        self.usercache = None if os.path.exists(cache) else cache
        self.folder = tempfile.mkdtemp(dir=mc_check.workdir())
        if getattr(self, "port", None) is None:      # a restart keeps the ports: the players join again (#979)
            self.port, self.game_port = mc_check.free_port(), mc_check.free_port()
        password = secrets.token_hex(16)
        with open(os.path.join(self.folder, "eula.txt"), "w") as f:
            f.write("eula=true\n")
        for p in plugins:
            os.makedirs(os.path.join(self.folder, "plugins"), exist_ok=True)
            shutil.copy(p, os.path.join(self.folder, "plugins", "aoe2mc-plugin.jar"))
        path = pack_file(self.world)
        self.pack = pack_source(path) if path else None
        with open(os.path.join(self.folder, "server.properties"), "w") as f:
            f.write(properties(self.game_port, self.port, password, self.pack))
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

    def batch(self, cmds):
        """Send cmds in this order and drop the answers. On Paper they go in `aoe batch` commands (`batches`): each
        RCON command waits for the main thread of the server, 2 to 5 ms at a tick of 45 ms, and the live replay of
        de-63.0 fell behind its clock after 16 minutes (#2761)."""
        for c in batches(cmds) if self.kind == "paper" else cmds:
            self.command(c)

    def op_joined(self):
        """Give operator rights to each player who joined since the last call (/gamemode, /tp without RCON, #292).
        The server listens only on 127.0.0.1, so only local players can join."""
        log = self.server.log
        new, self.seen = log[self.seen:], len(log)
        for line in new:
            if m := JOINED.search(line):
                self.command(f"op {m.group(1)}")
                self.joined = {*self.joined, m.group(1)}
                self.side(m.group(1))

    def side(self, name):
        """Put Minecraft player name on the team of its AoE2 player in a game of more people (decision #1308, option
        A): the join order. The first one gets player 1, the second player 2; a later one gets no side. A player who
        joins again keeps its side. A later menu (option C) changes this table only. A later one is a spectator (#2898):
        the game mode spectator flies through blocks and uses no items, and the team spec is no team of a player, so
        no Gather reads its clicks (Gather.who). With one person all Minecraft players play player 1 (who "@a")."""
        seats = getattr(self, "seats", ())          # co-op (#3489): two people can have the same player
        free = (seats[len(self.sides):] or [0])[0] if seats else \
            next((k for k in range(1, self.people + 1) if k not in self.sides.values()), 0)
        n = self.sides.get(name) or free
        if self.people > 1 and n:
            self.sides[name] = n
            self.command(f"team join p{n} {name}")
            for cmd in [f"aoe hide {name} team"] * (getattr(self, "kind", "paper") == "paper"):
                self.command(cmd)            # the hides of the own team only: the plugin hid all on the join (#3070)
            if name not in getattr(self, "placed", ()):   # a join again keeps the place (#3347)
                self.start_view(name, n)
            self.command(f"tellraw {name} " + json.dumps({"text": CHAT_HINT, "color": "gray"}))   # the chat targets (#3555)
        elif self.people > 1:
            for cmd in [*SPECTATORS * (not self.spectators), f"team join spec {name}", f"gamemode spectator {name}",
                        *[f"aoe show {name} all"] * (getattr(self, "kind", "paper") == "paper")]:
                self.command(cmd)                    # a join again: force-gamemode made it creative; the plugin hid
                                                     # the fog units of all teams on the join, with no team yet (#2921)
            self.spectators = {*self.spectators, name}

    def choose(self, name, n):
        """The menu "Choose your player" (lobby.py, #1563): Minecraft player name plays AoE2 player n, when no other
        Minecraft player has it. Returns False for a taken side."""
        if any(k == n for p, k in self.sides.items() if p != name):
            return False
        old = self.sides.get(name)
        self.sides[name] = n
        self.command(f"team join p{n} {name}")
        for cmd in [f"aoe hide {name} team"] * (getattr(self, "kind", "paper") == "paper"):
            self.command(cmd)                # a side change keeps the hides of the old team (#3070)
        if name in getattr(self, "spectators", ()):  # a spectator who takes a free side plays again (#2898)
            self.spectators = self.spectators - {name}
            self.command(f"gamemode creative {name}")
        if old != n:                         # the start view of the new side (#3350)
            self.start_view(name, n)
        return True

    def start_view(self, name, n):
        """Move Minecraft player name to the start block of AoE2 player n, and set its spawn point there (#3347)."""
        starts, yaw = getattr(self, "starts", {}), getattr(self, "yaw", 0.0)
        if n in starts:
            x, y, z = starts[n]
            self.command(f"tp {name} {x + 0.5} {y} {z + 0.5} {yaw} 0")
            self.command(f"spawnpoint {name} {x} {y} {z} {yaw} 0")   # the angle is yaw and pitch (#3596)
            self.placed = {*getattr(self, "placed", ()), name}

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
        if getattr(self, "pack", None):
            self.pack.stop()
            self.pack = None
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


class Side:
    """The Gather of a second person (#1310): Gather.run steps it as it steps a bot (Gather.bots), with the clicks of
    the Minecraft players of its team."""

    def __init__(self, g):
        self.g = g

    def step(self):
        import fog
        self.g.point()
        for name in self.g.clicks():
            self.g.click(name)
        self.g.step()
        fog.tick(self.g)                             # the fog of war of its team (#1631)


def bot_seat(players, people):
    """(player, foe) of the bot (#1794): it plays the player after the people, and attacks the first person who is
    not its ally (aoe2mc.json teams, gather.allied), else the first other player that is not its ally, else None: no
    enemy, no attack (#3107)."""
    import gather
    player = people + 1
    others = sorted(int(p) for p in players if int(p) > 0)
    return player, next((p for p in [*range(1, player), *others] if p != player
                         and not gather.allied(players, player, p)), None)


def pop_limit(text):
    """The value of --pop-limit: a population limit that AoE2 DE offers (train.LIMITS, #2266)."""
    import train
    if not text.isdigit() or int(text) not in train.LIMITS:
        raise argparse.ArgumentTypeError(f"{text} is no AoE2 population limit: use one of "
                                         + ", ".join(map(str, train.LIMITS)))
    return int(text)


def challenge_names():
    """The names of the Art of War challenges (challenge.CHALLENGES, #3900)."""
    import challenge
    return challenge.CHALLENGES


def civ_choices(values):
    """{player: civilization} of the --civ values ("1=BRITONS", #2267). An unknown name stops with the list of names."""
    import civs
    names, out = sorted(r["name"] for r in civs.ROWS), {}
    for v in values or ():
        player, _, name = v.partition("=")
        if not player.isdigit() or name.upper() not in names:
            sys.exit(f"--civ {v}: write PLAYER=CIVILIZATION, one of: {', '.join(names)}")
        out[int(player)] = name.upper()
    return out


def apply_civs(data, civs):
    """Write the --civ choices {player: civilization} into the players of aoe2mc.json. A player whose scenario locks
    its civilization ("Lock Civilizations", #3295) keeps the scenario civilization: a line on stderr says why."""
    for player, name in (civs or {}).items():
        p = data.setdefault("players", {}).setdefault(str(player), {})
        if p.get("lock_civ"):
            print(f"player {player}: the scenario locks its civilization, --civ {name} is not used", file=sys.stderr)
            continue
        p["civ"] = name


def handicap_choices(values):
    """{player: percent} of the --handicap values ("1=150", #2474): the AoE2 setting "Handicap", 100 to 200 in steps of
    5. A wrong value stops with a message."""
    out = {}
    for v in values or ():
        player, _, pct = v.partition("=")
        if not player.isdigit() or not pct.isdigit() or int(pct) not in range(100, 201, 5):
            sys.exit(f"--handicap {v}: write PLAYER=PERCENT, the percent 100 to 200 in steps of 5, for example 1=150")
        out[int(player)] = int(pct)
    return out


def team_choices(value, players):
    """{player: team or None} of the --teams value ("1,1,2,2", "-" is no team, #2296): one team for each player of
    aoe2mc.json "players" but Gaia, in player order. A wrong value stops with a message."""
    seats = sorted(int(p) for p in players if int(p) > 0)
    teams = value.split(",")
    if len(teams) != len(seats) or any(t not in ("1", "2", "3", "4", "-") for t in teams):
        sys.exit(f"--teams {value}: write {len(seats)} teams, one for each player in player order, each 1 to 4 or - "
                 f"(no team), for example --teams {','.join('12'[i % 2] for i in range(len(seats)))}")
    return {p: None if t == "-" else int(t) for p, t in zip(seats, teams)}


def seat_list(value):
    """The AoE2 player of each person in the join order of --seats ("1,1,2", decision #3488): two people on one
    player play it together (co-op, #3489). The players must be 1 to N with no gap. A wrong value stops with a message."""
    seats = [int(t) for t in value.split(",") if t.strip().isdigit()]
    if len(seats) != len(value.split(",")) or not seats or set(seats) != set(range(1, max(seats) + 1)):
        sys.exit(f"--seats {value}: write the AoE2 player of each person in join order, players 1 to N with no gap, "
                 "for example --seats 1,1,2")
    return seats


# The AoE2 game modes of --mode (epic #2263): the lines of game/data/setup.jsonl with a "help" (the --mode help text).
# Keys: "module" (its setup(g, mode) after the bots), "age" (the start age when --age is dark), "loaded" ("skip": no
# setup in a loaded game, "start": setup(..., start=False)), "bots" (the Gathers of the bots get the mode too). A new mode
# is one line there and its module, not a change of play() or main() (#2521).
MODES = {r["name"]: r for r in table.load("setup.jsonl") if "help" in r}
# The modes that a lobby option turns on on top of the --mode (AoE2 "Advanced Settings": "Sudden Death Mode (applies
# Sudden Death setting on top of the selected game mode)", #2490): --empire-wars, --regicide, --sudden-death.
ON_TOP = ("empire-wars", "regicide", "sudden-death")
VICTORIES = {                        # the AoE2 setting "Victory" (--victory, Gather.run): one per line, in alphabetical order
    "conquest": "only the conquest (#2316)",
    "king-of-the-hill": "the monument in the center (hill.py, #2360)",
    "last-man-standing": "a conquest that only one player wins (conquest.last_man, #2358)",
    "score": "the first player at the score target of --victory-value (time_limit.py, #2356)",
    "standard": "conquest, a wonder or all relics",
    "time-limit": "the highest score at the end of the years of --victory-value (time_limit.py, #2356)",
}


# The AoE2 lobby settings of play() for each player and bot (epic #2263), name: default. main() passes the option of
# the same name. A new setting is one line here, in alphabetical order, not a change of the play() lines (#2373).
SETTINGS = {
    "age": "dark",                    # "Starting age" (train.STARTS, #2265)
    "ai_difficulty": "standard",      # "AI difficulty" of the bots (bot.LEVELS, game/data/difficulty.jsonl, #2661)
    "all_techs": False,               # "All Techs" (civs.missing, #2298)
    "antiquity": False,               # Antiquity Mode: the Return of Rome rule set (table.use, game/data/antiquity, #3666)
    "challenge": None,                # an Art of War challenge (challenge.CHALLENGES, #3900)
    "civ": None,                      # {player: civilization} in place of the scenario's (civ_choices, #2267)
    "empire_wars": False,             # "Empire Wars Mode" on top of the mode (ON_TOP, #2490)
    "end_age": "imperial",            # "Ending age" (build.locked, #2346)
    "full_tech_tree": False,          # "Full Tech Tree": the full tech tree and no civilization bonuses (civs.civ, #2354)
    "handicap": None,                 # {player: percent} "Handicap" (civs.handicap, handicap_choices, #2474)
    "mode": "standard",               # the game mode (MODES: its line in game/data/setup.jsonl and its module, #2521)
    "pop_limit": None,                # "Population limit" (train.LIMITS, #2266)
    "record": None,                   # "Record Game": the file of the timeline of the game (record.py, #2649)
    "regicide": False,                # "Regicide Mode" on top of the mode (ON_TOP, #2490)
    "resources": "standard",          # "Starting resources" (gather.LEVELS, #2264)
    "shared_exploration": "on",       # "Shared Exploration": "off" takes the sight of the allies away (fog.shares, #2602)
    "sudden_death": False,            # "Sudden Death Mode" on top of the mode (ON_TOP, #2490)
    "teams": None,                    # {player: team or None} in place of the scenario's (team_choices, #2296)
    "treaty": "0:00",                 # "Treaty length" (MM:SS): before it no player can attack another (treaty.py, #2297)
    "turbo": False,                   # "Turbo Mode" (civs.turbo, #2359)
    "unlock_speed": False,            # "Lock Speed" off: the button "Game speed" of the Game menu (diplomacy.faster, #2933)
    "unlock_teams": False,            # "Lock Teams" off: the stance row of the Diplomacy page (diplomacy.STANCES, #2934)
    "victory": "standard",            # "Victory" (VICTORIES)
    "victory_value": None,            # the years of "time-limit", the points of "score" (time_limit.YEARS, POINTS)
}


def mode_defaults(settings):
    """The start resources of the game mode in place of the default of SETTINGS (a --resources that the player gave
    wins): the key "level" of its line in game/data/setup.jsonl. Death Match starts with "ultra" (#2438). The start age
    of a mode ("age") applies in play() when --age is dark."""
    if "level" in MODES[settings["mode"]] and settings["resources"] == SETTINGS["resources"]:
        settings["resources"] = MODES[settings["mode"]]["level"]
    return settings


def scenario_modes(settings, data):
    """Turn on the secondary game modes of the scenario (aoe2mc.json "victory" "modes", #3297) in the scenario mode, as
    the lobby options of ON_TOP do. A lobby option of the person stays on. King of the Hill is a victory (scenario.setup)."""
    if settings["mode"] == "scenario":
        for m in set((data.get("victory") or {}).get("modes", ())) & set(ON_TOP):
            settings[m.replace("-", "_")] = True
    return settings


def start_places(data):
    """The start block of each AoE2 player and the spawn yaw of aoe2mc.json (#3347): (starts, yaw)."""
    starts = {int(k): tuple(p["start"]) for k, p in data["players"].items() if "start" in p}
    return starts, data.get("yaw", 0.0)


def play(game, world, log=None, cheats=False, bot=False, seconds=None, bot_attack="10:00", reveal="normal", people=1,
         speed=1.0, state=None, wait=False, **settings):
    """state: the saved state of the players (savegame.dump) for a loaded game (#2255).
    wait: freeze the ticks now, and start the game when the people joined (start_on_join, #3314).
    settings: the AoE2 lobby settings (SETTINGS); a missing one has its default."""
    if wait:                                         # the trigger timers start at the join, not at the load
        game.command("tick freeze")
        game.command("scoreboard players set #wait aoe_trig 1")   # the tick triggers too (aoe2mc.WAIT, #3892)
    import gather, train
    if unknown := sorted(set(settings) - set(SETTINGS)):
        raise TypeError(f"play() has no setting {', '.join(unknown)} (SETTINGS)")
    settings = mode_defaults({**SETTINGS, **settings})

    players = max(getattr(game, "seats", ()), default=people)   # --seats: fewer players than people (#3489)

    def make(player):
        who = "@a" if people == 1 else f"@a[team=p{player}]"
        saved = ((state or {}).get("players", {}).get(str(player)) or {}).get("villagers")   # the living at the save (#3109)
        for _ in range(60):                          # entities load in other threads
            g = gather.Gather(game, data, player=player, log=log, cheats=cheats, resources=settings["resources"],
                              pop_limit=settings["pop_limit"])
            g.who = who
            g.setup()
            if all(o["uuid"] in g.villagers for o in g.units if saved is None or o["uuid"] in saved):
                return g
            time.sleep(1)
        return g
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    scenario_modes(settings, data)
    if settings["challenge"]:                                    # the civilization of the challenge (#3900)
        import challenge
        settings["civ"] = {**(settings["civ"] or {}), 1: challenge.CHALLENGES[settings["challenge"]]["civ"]}
    apply_civs(data, settings["civ"])                             # before the Gathers: all bonuses (civs.civ) follow it
    for player, pct in (settings["handicap"] or {}).items():     # before the Gathers: the start resources (#2474)
        data.setdefault("players", {}).setdefault(str(player), {})["handicap"] = pct
    for player, team in (settings["teams"] or {}).items():       # gather.allied and the scoreboard teams follow it
        data["players"][str(player)]["team"] = team
    data["all_techs"] = settings["all_techs"]                    # one data for all Gathers: the people and the bot (#2298)
    data["end_age"] = train.STARTS[settings["end_age"]]["ages"]  # the last age (build.locked, #2346)
    data["full_tech_tree"] = settings["full_tech_tree"]          # (#2354)
    data["turbo"] = settings["turbo"]                            # (#2359)
    data["unlock_teams"] = settings["unlock_teams"]              # diplomacy.items (#2934)
    data["shared_exploration"] = settings["shared_exploration"] == "on"   # fog.shares (#2602)
    data["resources"] = settings["resources"]                    # the Regicide start resources of the level (#2388)
    if settings["resources"] in gather.RANDOM:                   # each Gather picks the same level (gather.level, #2489)
        print(f"Random starting resources: {gather.level(settings['resources'], data)}.", file=sys.stderr)
    game.forceload()
    game.people = people
    g = make(1)
    g.reveal = reveal                                # "all": no fog of war for the units (fog.py, #1389)
    g.victory = settings["victory"]                              # Gather.run: the wonder and relic wins only in "standard"
    g.victory_value = settings["victory_value"]                  # time_limit.tick (#2356)
    g.challenge = settings["challenge"]                          # challenge.tick (#3900)
    g.unlock_speed = settings["unlock_speed"]                    # the Game menu of player 1 (diplomacy.faster, #2933)
    if people > 1:                                   # one Gather for each person, in the join order (#1308, #1310)
        g.bots = [Side(make(n)) for n in range(2, players + 1)]
        for s in g.bots:                             # the same trees, bushes and mines, as with a bot
            s.g.map.trees, s.g.map.bushes, s.g.map.mines = g.map.trees, g.map.bushes, g.map.mines
            s.g.relics = g.relics                    # one list: each relic exists once (#3116)
            s.g.reveal, s.g.peers = reveal, [g, *(o.g for o in g.bots)]   # its fog sees all units (#1631)
            s.g.unlock_speed = settings["unlock_speed"]          # each person has the Game menu (#2933)
        game.starts, game.yaw = start_places(data)   # the start views and the spawn yaw (#3347)
        for name in list(game.sides):                # players who joined before the teams were there
            game.side(name)
        first = [*getattr(game, "seats", ()), 1, 2][:2] if getattr(game, "seats", ()) else [1, 2]
        print(f"{people} people: the first Minecraft player who joins plays player {first[0]}, the second player "
              f"{first[1]}.", file=sys.stderr)
    if settings["mode"] == "scenario":               # the computer players of the scenario, not --bot (#2543)
        import scenario
        seats = scenario.bot_seats(data["players"], players)
    else:
        seats = [bot_seat(data["players"], players)] if bot else []
    for player, foe in seats:                        # after the people, next to their Sides (#1794)
        import bot as bots
        import replay
        import treaty as treaties
        attack = max(bot_attack, settings["treaty"], key=replay.aoe2mc.game_time)   # the bot waits for the treaty too
        if settings["mode"] in treaties.ENDLESS or foe is None:   # Wonder Race (#2406), no enemy (#3107): no attack
            attack = "never"
        g.bots = [*g.bots, bots.Bot(game, data, player=player, share=g, log=log, foe=foe,
                                    attack=math.inf if attack == "never" else replay.aoe2mc.game_time(attack) / 1000,
                                    resources=settings["resources"], pop_limit=settings["pop_limit"],
                                    difficulty=settings["ai_difficulty"]).setup()]
        at = math.inf if attack == "never" else \
            replay.aoe2mc.game_time(attack) / 1000 * bots.LEVELS[settings["ai_difficulty"]]["attack"]
        print(f"A bot ({settings['ai_difficulty']}) plays player {player}: {len(g.bots[-1].g.villagers)} villagers "
              f"gather, its soldiers attack {'no player (no enemy)' if foe is None else f'player {foe}'} "
              f"{'never' if at == math.inf else 'at %d:%02d' % divmod(round(at), 60)}.", file=sys.stderr)
    import combat
    combat.setup(game, data)                         # AoE2 hit points and damage (#514)
    modes = {settings["mode"], *(m for m in ON_TOP if settings[m.replace("-", "_")])} - {"standard"}   # (#2490)
    if settings["age"] == "dark" and (ages := [MODES[m]["age"] for m in modes if "age" in MODES[m]]):   # (#2408)
        import train                                             # the latest start age of the modes (#2441)
        settings["age"] = max(ages, key=lambda a: train.STARTS[a]["ages"])
    for x in [g, *(s.g for s in g.bots)]:                        # before the age: train.research sets the scores (#3089)
        x.modes = frozenset(modes)                               # gather.has_mode: build.locked, Gather.run (#2490)
        if MODES[settings["mode"]].get("bots") or x is g:
            x.mode = settings["mode"]                            # build.locked of each player (#2407)
    if not state and settings["age"] != "dark":                  # after the base values: the technologies change them
        import train
        for x in [g, *(s.g for s in g.bots)]:
            train.start(x, settings["age"])
    if settings["record"]:                                       # the orders of the people and the bots (#2649), and
        import record                                            # the objects of the setups below at 0:00 (#3028)
        record.start([g, *(b.g for b in g.bots)], settings["record"])
    import scout
    if not state and scout.used(data):               # the scout of each civilization (#2391), not twice after a load
        for x in [g, *(s.g for s in g.bots)]:
            scout.swap(x)
    import start_buildings
    if not state and start_buildings.used(data):     # the Georgian mule cart (#2429), not twice after a load
        for x in [g, *(s.g for s in g.bots)]:
            start_buildings.place(x)
    if state:                                                    # before the modes and the minimap: they see the save
        import savegame                                          # (the Wonder, the defeated, the sites, #2981)
        savegame.load(g, state)
    for mode in sorted(modes):                                   # after the age: the town of Empire Wars, the Wonder;
        line = MODES[mode]                                       # the Kings go to the Gathers of the bots (#2347)
        if "module" in line and not (state and line.get("loaded") == "skip"):   # a loaded game has its town, relic
            start = {"start": not state} if line.get("loaded") == "start" else {}   # Defend the Wonder (#2441)
            importlib.import_module(line["module"]).setup(g, mode, **start)
    import replay
    import treaty as treaties
    if settings["mode"] in treaties.ENDLESS:                     # Wonder Race: a treaty with no end (#2406)
        treaties.start(g, math.inf, (state or {}).get("treaty_time", 0.0))
    elif replay.aoe2mc.game_time(settings["treaty"]):            # after the Gathers: they set the neutral stances
        treaties.start(g, replay.aoe2mc.game_time(settings["treaty"]) / 1000, (state or {}).get("treaty_time", 0.0))   # #2409
    if settings["record"]:                                       # the setups end, the game starts (#3028)
        import record
        record.play([g, *(b.g for b in g.bots)])
    if game.kind == "paper":                         # the view square of each player on map 0 (#1762)
        import replay
        game.command("aoe minimap on")               # the dots of the units, as in the live replay (#2581)
        import build
        for c in build.minimap(g):                   # the squares of the buildings (#2582)
            game.command(c)
        game.command(f"aoe minimap frame {replay.FRAME * data['tile_size']}")
    print(f"Join the server localhost:{game.game_port} (Minecraft {game.version}, multiplayer, direct connection).\n"
          f"{len(g.villagers)} villagers of player 1. Hold the carrot on a stick: right click a villager to select it,\n"
          "then right click a tree, a fruit bush or a mine. To build: /trigger aoe_build set N (the menu is in the chat),\n"
          "then right click the ground. Right click your town center to train a villager (50 food). Ctrl-C stops.", file=sys.stderr)
    if people > 1:                                   # this console only: a person gets it in the chat on the join (#3555)
        print(CHAT_HINT, file=sys.stderr)
    game.g = g                                       # main saves its state on Ctrl-C (#2255)
    if speed != 1:                                   # Minecraft makes the mobs, paths and plugin faster (#2057)
        import savegame
        game.command(f"tick rate {TICKS * speed:g}")
        g.speed = speed
        for h in savegame.sides(g)[1:]:              # the bots keep the game time of player 1 (#3513)
            h.speed = speed
    if wait:
        import savegame
        start_on_join(game, savegame.sides(g), people)
    g.run(seconds)
    if g.ended:
        unveil(g)
    return g


def start_on_join(game, sides, people, sleep=time.sleep):
    """As in AoE2 DE, the game starts when all people are there (#3314): play froze the ticks (the `schedule` timers
    of the scenario triggers, the mobs) at the start of play(). Unfreeze them after the join of the people, and start
    the game clock of each side (Gather.t0) then, so that the triggers, the treaty and the bots agree."""
    print(f"The game starts when {people} {'person' if people == 1 else 'people'} joined.", file=sys.stderr)
    while len(game.joined) < people:
        sleep(0.5)
    import gather
    game.command("scoreboard players reset #wait aoe_trig")
    game.command("tick unfreeze")
    show_titles(game)                                # nobody saw a title before the join (#3772)
    for h in sides:                                                    # a loaded game goes on at its saved game time (#3377)
        h.t0 = h.clock() - vars(game).get("loaded_seconds", 0.0) / (gather.NORMAL * getattr(h, "speed", 1.0))


def show_titles(game):
    """The campaign name as title and "Scenario N: name" as subtitle to all players online (#3506)."""
    if titles := vars(game).get("titles"):
        game.command(f"title @a subtitle {json.dumps(titles[1])}")
        game.command(f"title @a title {json.dumps(titles[0])}")


def unveil(g):
    """As in AoE2, no fog of war after "Victory" or "Defeat": all units of all players show (#2051)."""
    import fog
    for x in [g, *(getattr(s, "g", None) for s in g.bots)]:
        if x is not None and x.reveal != "all":
            fog.toggle(x)


TICKS = 20                                           # the normal Minecraft tick rate: game ticks per second


KEEP = ("playerdata", "stats", "advancements", "session.lock")   # the players stay where they are after a restart


def save(game):
    """A copy of the world of the running server (save-all flush first). Returns its folder."""
    game.command("save-off")                         # no autosave while it copies
    game.command("save-all flush")
    folder = tempfile.mkdtemp(dir=mc_check.workdir())
    shutil.copytree(game.world, folder, dirs_exist_ok=True, ignore=lambda d, names: [n for n in names if n in KEEP])
    game.command("save-on")
    return folder


def restore(saved, world):
    """Put the world back to the copy of `save` (the server is stopped). The player files stay."""
    for name in set(os.listdir(world)) - set(KEEP):
        path = os.path.join(world, name)
        shutil.rmtree(path) if os.path.isdir(path) and not os.path.islink(path) else os.remove(path)
    shutil.copytree(saved, world, dirs_exist_ok=True)


def replay(game, world, speed=1.0, start="0:00", follow=None, guide=None, view=None, replay_file=None, camera=False):
    """guide: a poll(control) next to the hotbar input that gets `input` and the replay `r` (game/watch.py, #1123).
    view: the replay starts with the view of player N (#1303: the units out of its sight are hidden).
    replay_file: the timeline of a game of --play --record on this world in place of the one of aoe2mc.json (#2649)."""
    import replay
    start = replay.aoe2mc.game_time(start)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    if replay_file:
        import record
        data = record.apply(data, replay_file)
    if "timeline" not in data:
        sys.exit("--replay needs a world of a recorded game (.aoe2record)")
    import replay_input
    control = replay_input.Input(game)              # hotbar items, menu and /trigger aoe_replay (#688)
    if guide:
        guide.input = control

    def setup():
        game.forceload()
        if game.kind == "paper":                     # the start units and buildings fight with AoE2 values (#632)
            import combat
            combat.setup(game, data)
        control.setup()
    setup()
    saved = save(game)                               # the start state for a jump back (#979)

    def restart():
        print("Jump back: the server restarts on the start world.", file=sys.stderr)
        game.stop()
        restore(saved, game.world)
        game.start()
        setup()
    print(f"Join the server localhost:{game.game_port} (Minecraft {game.version}). The replay starts now "
          f"at speed {speed}. Right click the items in your hotbar, or /trigger aoe_replay set N.", file=sys.stderr)
    def make():
        r = replay.Replay(game, data, game.version, ai=game.kind == "paper", follow=follow, pov=view, camera=camera)
        if guide:
            guide.r = r
        return r
    try:
        stats = replay.live(make, speed, start, restart, bar=True, poll=guide or control)
    finally:
        shutil.rmtree(saved, ignore_errors=True)
    print(f"{stats['events']} events, {stats['commands']} commands in {stats['busy']} s "
          f"({stats['rate']} commands per second, the timeline needs {stats['need']}), largest lag {stats['lag']} s")
    return stats


CONSOLE = {}                                         # the one stdin thread and the game that gets its lines (#3812)


def console(game):
    """A thread that sends each line of stdin to the server and prints the answer, also while a replay or a game runs
    (#1777: the command line of the window, gui.py). It ends at the end of stdin (EOF). The next scenario of a
    campaign keeps the thread and gets its lines: a second thread would take every other line (#3812)."""
    CONSOLE["game"] = game
    if (t := CONSOLE.get("thread")) and t.is_alive():
        return t

    def read():
        for line in sys.stdin:
            if line.strip() == STOP_LINE:            # the Stop of the window on Windows (gui.stop_game, #3003)
                interrupt()
            elif line := line.strip().lstrip("/"):
                try:
                    print(CONSOLE["game"].command(line), flush=True)
                except Exception as e:                # one failed command (too long, no server) keeps the line open
                    print(f"The command failed: {e}", file=sys.stderr, flush=True)
    t = CONSOLE["thread"] = threading.Thread(target=read, daemon=True)
    t.start()
    return t


def interrupt():
    """A KeyboardInterrupt in the main thread, as Ctrl-C gives, also when it sleeps (#3003)."""
    if hasattr(signal, "pthread_kill"):
        signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)
    else:                                            # Windows: the C handler of SIGINT also wakes a sleep of the main thread
        signal.raise_signal(signal.SIGINT)


def given(ap, argv):
    """The names (dest) of the options of ap that the command line argv gives: parse it with no defaults."""
    defaults = [(x, x.default) for x in ap._actions]
    for x, _ in defaults:
        x.default = argparse.SUPPRESS
    try:
        return set(vars(ap.parse_args(argv)))
    finally:
        for x, d in defaults:
            x.default = d


def ctrl_c():
    """Ctrl-C (and the Stop of the window, gui.stop_game) stops the game with a KeyboardInterrupt. Python keeps a SIGINT
    that the parent ignores (a background job, nohup): then the game did not stop, and gui.stop_game killed the server
    after 30 s with no save (#2658)."""
    signal.signal(signal.SIGINT, signal.default_int_handler)
    if hasattr(signal, "SIGBREAK"):                  # Windows: Ctrl-Break in a console (the window sends STOP_LINE, #3003)
        signal.signal(signal.SIGBREAK, signal.default_int_handler)


def campaign(folder, number=None):
    """The folder of a converted campaign (campaign.json, #3505) -> (world folder, name, "Scenario N: <name>", N) of
    scenario N, default the first open one of progress.json (#3507), else the first converted one (#3506). A wrong or
    not converted N stops with the open ones."""
    with open(os.path.join(folder, "campaign.json"), encoding="utf-8") as f:
        index = json.load(f)
    open_ = [s for s in index["scenarios"] if s.get("converted", True)]
    if number is None:                               # the lowest scenario that is not won: its earlier ones are won
        won = set(progress(folder))
        number = next((s["number"] for s in sorted(open_, key=lambda s: s["number"]) if s["number"] not in won), None)
    pick = next((s for s in open_ if number is None or s["number"] == number), None)
    if pick is None:
        sys.exit(f"--scenario {number}: no converted scenario {number} in {index['name']}. Open scenarios: "
                 + ", ".join(f"{s['number']} ({s['name']})" for s in open_))
    return os.path.join(folder, pick["world"]), index["name"], f"Scenario {pick['number']}: {pick['name']}", pick["number"]


def progress(folder):
    """The numbers of the won scenarios of a campaign folder (progress.json, #3507)."""
    return progress_file(folder).get("won", [])


def progress_file(folder):
    """The content of progress.json of a campaign folder: "won", "difficulty" (#3507, #3520)."""
    try:
        with open(os.path.join(folder, "progress.json"), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def campaign_difficulty(folder, chosen):
    """AoE2 DE: one difficulty for the whole campaign (#3520). The first start writes the chosen one into
    progress.json, a later start keeps the value of the file."""
    kept = progress_file(folder).get("difficulty")
    if kept is None:
        write_progress(folder, difficulty=chosen)
        return chosen
    if kept != chosen:
        print(f"The campaign difficulty is {kept}.", file=sys.stderr)
    return kept


def campaign_keys(folder):
    """The key values of the played scenarios of a campaign folder (progress.json "keys", #3508)."""
    try:
        with open(os.path.join(folder, "progress.json"), encoding="utf-8") as f:
            return json.load(f).get("keys", {})
    except FileNotFoundError:
        return {}


def advance(folder, number, won):
    """The end of scenario number of a campaign (#3507): a victory goes into progress.json and gives the next
    converted scenario, a loss gives the same one again. None: the last scenario is won."""
    if not won:
        return number
    done = sorted(set(progress(folder)) | {number})
    write_progress(folder, won=done)
    with open(os.path.join(folder, "campaign.json"), encoding="utf-8") as f:
        later = [s["number"] for s in json.load(f)["scenarios"] if s.get("converted", True) and s["number"] > number]
    return min(later, default=None)


def write_progress(folder, **values):
    """Set the keys of progress.json of a campaign folder; the other keys stay."""
    path = os.path.join(folder, "progress.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data | values, f)


STORAGE = os.path.join("data", "aoe2mc", "command_storage.dat")   # the data storages aoe2mc:* of a 26.3 world (#3508, #3771)


def world_keys(world):
    """The key values of the trigger effect "Store Key Value" (aoe2mc.key_lines: storage aoe2mc:keys) of a world."""
    from nbtlib import load
    try:
        values = load(os.path.join(world, STORAGE))["data"]["contents"]["keys"]["values"]
    except (FileNotFoundError, KeyError):
        return {}
    return {k: int(v) for k, v in values.items()}


def put_keys(world, values):
    """Add the key values to the storage aoe2mc:keys of a world: a given key wins, a key of the world only stays.
    The other storages stay."""
    if not values:
        return
    from nbtlib import File, load
    from nbtlib.tag import Compound, Int
    path = os.path.join(world, STORAGE)
    try:
        root = load(path)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import aoe2mc
        root = File({"DataVersion": Int(aoe2mc.DATA_VERSION), "data": Compound({"contents": Compound()})}, gzipped=True)
    keys = root["data"]["contents"].setdefault("keys", Compound())
    keys["values"] = Compound(dict(keys.get("values", {})) | {k: Int(v) for k, v in values.items()})
    root.save(path, gzipped=True)


def carry_keys(old, new):
    """The key values of the world old go into the world new, as AoE2 DE keeps them in a campaign (#3508)."""
    put_keys(new, world_keys(old))


def fresh(folder, world):
    """Each start of a campaign scenario plays the converted world, not the one of an earlier game: the first start
    keeps a copy in <folder>/.start, a later start puts it back (#3507)."""
    keep = os.path.join(folder, ".start", os.path.basename(world))
    if os.path.isdir(keep):
        restore(keep, world)
    else:
        shutil.copytree(world, keep, ignore=shutil.ignore_patterns(*KEEP))


PAUSE = 5                                            # seconds to read the end title before the server stops


def main(argv=None, scenario=None):
    """scenario: the next scenario of a campaign, after the end of one (#3507)."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("--scenario", type=int, metavar="N", help="a campaign folder (campaign.json): play its scenario N "
                    "(default: the first one) in the scenario mode")
    ap.add_argument("--version", default=mc_check.DEFAULT_VERSION, help="Minecraft version of the world")
    ap.add_argument("--server", choices=["paper", "vanilla"], default="paper", help="server program (default: Paper)")
    ap.add_argument("--bench", type=int, metavar="N", help="send N commands, print the commands per second, stop")
    ap.add_argument("--play", action="store_true", help="play: villagers of player 1 gather resources (aoe2mc.json)")
    ap.add_argument("--replay", action="store_true", help="replay the timeline of a recorded game (aoe2mc.json)")
    ap.add_argument("--speed", type=float, default=1.0, help="--replay, --play: times the game speed "
                    "(default 1; --play: the server ticks faster too)")
    ap.add_argument("--from", dest="start", default="0:00", metavar="MM:SS", help="--replay: start at this game time")
    ap.add_argument("--camera", choices=["auto"], help="--replay: the spectators move to each fight and group of new buildings (#3367)")
    ap.add_argument("--follow", type=int, metavar="N", help="--replay: the spectators follow the units of player N")
    ap.add_argument("--view", type=int, default=0, metavar="N", help="--replay: start with the view of player N: the "
                    "units out of its sight are hidden (default 0: all players)")
    ap.add_argument("--cheats", action="store_true", help="--play: the AoE2 cheat codes in the chat (off as in AoE2)")
    ap.add_argument("--bot", action="store_true", help="--play: a bot plays the player after the people (player 2 "
                    "with one person, player 3 with --people 2) and attacks them (game/bot.py)")
    ap.add_argument("--people", type=int, default=1, metavar="N", help="--play: N people play players 1 to N, in the "
                    "order in which they join (#1310); with --bot the bot plays player N + 1")
    levels = [r["name"] for r in table.load("difficulty.jsonl")]           # in the order of the AoE2 lobby
    ap.add_argument("--ai-difficulty", choices=levels, default="standard", help="--bot: the AoE2 setting \"AI "
                    f"difficulty\" ({', '.join(levels)}; default standard): the gather rate of the bot, the time of "
                    "its first attack (times --bot-attack) and the soldiers of its first wave")
    ap.add_argument("--bot-attack", default="10:00", metavar="MM:SS", help="--bot: its soldiers attack its foe "
                    "from this game time (default 10:00)")
    ap.add_argument("--treaty", default="0:00", metavar="MM:SS", help="--play: the AoE2 setting \"Treaty length\": "
                    "no player can attack another player before this game time (default 0:00: no treaty)")
    ap.add_argument("--reveal", choices=["normal", "explored", "all"], default="normal", help="--play: AoE2 \"Reveal "
                    "map\" (default normal: enemy units out of sight are hidden; explored: also, but the whole map "
                    "starts explored on the minimap; all: all units show)")
    ap.add_argument("--age", choices=["dark", "feudal", "castle", "imperial", "post-imperial"], default="dark",
                    help="--play: the AoE2 setting \"Starting age\" of each player, with the technologies of the "
                    "earlier ages (default dark; post-imperial: all technologies)")
    ap.add_argument("--antiquity", action="store_true", help="--play: Antiquity Mode, the rules of Return of Rome: "
                    "the Stone, Tool, Bronze and Iron Age (game/data/antiquity; only with --mode standard)")
    ap.add_argument("--end-age", choices=["dark", "feudal", "castle", "imperial"], default="imperial",
                    help="--play: the AoE2 setting \"Ending age\": the last age that the players can reach (default "
                    "imperial)")
    ap.add_argument("--resources", choices=["standard", "low", "medium", "high", "ultra", "infinite", "random"],
                    default="standard", help="--play: the AoE2 setting \"Starting resources\" of each player (default "
                    "standard; ultra: the Death Match resources; infinite: a cost does not lower the resources; "
                    "random: one of the levels low to ultra, the same for all players)")
    ap.add_argument("--all-techs", action="store_true", help="--play: the AoE2 setting \"All Techs\": each civilization "
                    "has the generic units and technologies that its tech tree does not have (the bonuses stay)")
    ap.add_argument("--full-tech-tree", action="store_true", help="--play: the AoE2 setting \"Full Tech Tree\": each "
                    "civilization has the full tech tree and its unique units, but no civilization and team bonuses")
    ap.add_argument("--victory", choices=sorted(VICTORIES), default="standard", help="--play: the AoE2 setting "
                    "\"Victory\" (default standard; " + "; ".join(f"{k}: {v}" for k, v in sorted(VICTORIES.items())
                                                       if k != "standard") + ")")
    ap.add_argument("--challenge", choices=sorted(challenge_names()), metavar="NAME", help="--play: an AoE2 \"Art "
                    "of War\" challenge with its civilization, goal and medals: " + ", ".join(sorted(challenge_names())))
    ap.add_argument("--victory-value", type=int, metavar="N", help="--play: the years of --victory time-limit "
                    "(default 500) or the points of --victory score (default 10000)")
    ap.add_argument("--pop-limit", type=pop_limit, default=200, metavar="N",
                    help="--play: the AoE2 setting \"Population limit\" of each player: 25 to 250 in steps of 25, 300, "
                    "400 or 500 (default 200)")
    ap.add_argument("--shared-exploration", choices=["on", "off"], default="on", help="--play: the AoE2 setting "
                    "\"Shared Exploration\" (default on: allies share their line of sight; off: each player sees only "
                    "through the own units and buildings)")
    ap.add_argument("--turbo", action="store_true", help="--play: the AoE2 setting \"Turbo Mode\": buildings, "
                    "gatherers and builders work 2.5 times faster (not villagers, trade units, castles, towers, wonders)")
    ap.add_argument("--unlock-speed", action="store_true", help="--play: the AoE2 setting \"Lock Speed\" off: the "
                    "button \"Game speed\" of the Game menu changes the speed of the game (1, 1.5, 2, as --speed)")
    ap.add_argument("--unlock-teams", action="store_true", help="--play: the AoE2 setting \"Lock Teams\" off: each "
                    "player sets its stance (ally, neutral, enemy) to each other player on the Diplomacy page")
    ap.add_argument("--mode", choices=sorted(MODES), default="standard", help="--play: the AoE2 game mode (default "
                    "standard; " + "; ".join(f"{k}: {v['help']}" for k, v in sorted(MODES.items()) if k != "standard") + ")")
    ap.add_argument("--empire-wars", action="store_true", help="--play: the AoE2 setting \"Empire Wars Mode\" on top "
                    "of --mode: a town and 27 villagers at work at the start")
    ap.add_argument("--regicide", action="store_true", help="--play: the AoE2 setting \"Regicide Mode\" on top of "
                    "--mode: each player has a King, a player whose King dies is defeated")
    ap.add_argument("--sudden-death", action="store_true", help="--play: the AoE2 setting \"Sudden Death Mode\" on top "
                    "of --mode: one town center, a player who loses it is defeated")
    ap.add_argument("--record", metavar="FILE", help="--play: the AoE2 setting \"Record Game\": write the orders of the "
                    "game into FILE (one JSON line per timeline event); --replay --replay-file FILE plays them again")
    ap.add_argument("--replay-file", metavar="FILE", help="--replay: play the timeline of a game of --play --record on "
                    "this world in place of the one of aoe2mc.json")
    ap.add_argument("--log", metavar="FILE", help="--play: write one JSON line per villager event (time, state, load)")
    ap.add_argument("--load", metavar="SAVE", help="--play: go on with a saved game (a folder of saves/: the end of "
                    "--play with Ctrl-C saves the world and the resources, technologies and ages there)")
    ap.add_argument("--civ", action="append", metavar="N=CIV", help="--play: player N plays civilization CIV (for "
                    "example 1=BRITONS, repeat it for more players): the game rules change, the buildings of the "
                    "world keep the architecture of the scenario")
    ap.add_argument("--handicap", action="append", metavar="N=PCT", help="--play: the AoE2 setting \"Handicap\" of "
                    "player N, 100 to 200 percent in steps of 5 (for example 1=150, repeat it for more players): more "
                    "start resources, villager work rate and hit points, building hit points and military building "
                    "work rate (default 100)")
    ap.add_argument("--seats", metavar="N,N,...", help="--play: the AoE2 player of each person in the order in which "
                    "they join, for example 1,1,2: the first two people play player 1 together (co-op), the third "
                    "player 2 (replaces --people)")
    ap.add_argument("--teams", metavar="T,T,...", help="--play: the team of each player in player order, 1 to 4 or - "
                    "(no team), for example 1,1,2,2: allies do not fight and share their team bonuses (default: the "
                    "teams of the scenario)")
    a = ap.parse_args(argv)
    if a.camera and a.follow is not None:
        ap.error("--camera auto and --follow N both move the spectators: give only one of them")
    import savegame
    state = savegame.read(a.load) if a.load else None
    if state:                                        # the settings of the save, but the options given here win (#2325)
        savegame.settings(a, state, given(ap, argv))
    if a.antiquity and (a.replay or a.mode != "standard"):
        sys.exit("--antiquity plays only --mode standard, and not --replay (the records are AoE2 games)")
    table.use("antiquity" if a.antiquity else "aoe2")   # before the first rule module loads (civ_choices, #3666)
    civ = civ_choices(a.civ)
    handicap = handicap_choices(a.handicap)
    import train
    if min(train.STARTS[a.age]["ages"], 3) > train.STARTS[a.end_age]["ages"]:   # post-imperial is the Imperial Age
        sys.exit(f"--age {a.age} is after --end-age {a.end_age}: the game must start in or before its last age")
    if scenario is not None:                         # the next scenario of the campaign starts fresh
        a.scenario, a.load, state = scenario, None, None
    titles, folder, after = None, None, None
    if not os.path.isfile(os.path.join(a.world, "level.dat")) and os.path.isfile(os.path.join(a.world, "campaign.json")):
        folder = a.world
        a.world, *titles, number = campaign(folder, a.scenario)
        a.mode = "scenario"
        a.ai_difficulty = campaign_difficulty(folder, a.ai_difficulty)
        if not a.load:
            fresh(folder, a.world)
            put_keys(a.world, campaign_keys(folder))     # the keys of the scenarios before it (#3508)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    teams = None
    if a.teams is not None:
        with open(os.path.join(a.world, "aoe2mc.json")) as f:
            teams = team_choices(a.teams, json.load(f).get("players", {}))
    if a.load:                                       # the saved world replaces the world (the player files stay)
        restore(os.path.join(a.load, "world"), a.world)
    ctrl_c()
    game = Game(a.world, a.version, server=a.server)
    if a.seats:                                      # co-op (#3489): one person for each seat
        game.seats = seat_list(a.seats)
        a.people = len(game.seats)
    game.people = a.people                           # the join order counts from the first player (#1310)
    game.settings = {k: getattr(a, k) for k in savegame.SETTINGS}   # savegame.dump keeps them (#2325)
    try:
        game.start()
        print(f"Server is ready. RCON on 127.0.0.1:{game.port}. Ctrl-C stops the server.", file=sys.stderr)
        if a.bench:
            print(f"{bench(game, a.bench):.0f} commands per second through RCON")
            return
        commands = console(game)                     # type commands at any time (#1777)
        game.titles = titles or ()                   # the campaign and the scenario name (#3506)
        if not (a.play and not a.replay):            # else start_on_join sends them after the join (#3772)
            show_titles(game)
        if a.replay:                                 # after the end the player can look around (#978)
            replay(game, a.world, a.speed, a.start, a.follow, view=a.view or None, replay_file=a.replay_file,
                   camera=a.camera == "auto")
            print("The replay ended. The server stays up: type commands, Ctrl-C stops it.", file=sys.stderr)
        if a.play:
            with open(a.log, "w") if a.log else contextlib.nullcontext() as log:
                g = play(game, a.world, log, a.cheats, a.bot, bot_attack=a.bot_attack, reveal=a.reveal,
                         people=a.people, speed=a.speed, state=state, wait=not a.replay,
                         **{k: getattr(a, k) for k in SETTINGS} | {"civ": civ, "teams": teams, "handicap": handicap})
            if not getattr(g, "ended", None):
                return
            if folder:                               # a campaign goes on with the next or the same scenario (#3507)
                game.command("save-all flush")      # the server writes the storage of the keys now (#3771)
                if keys := campaign_keys(folder) | world_keys(a.world):   # the keys go into the next scenario (#3508)
                    write_progress(folder, keys=keys)
                after = advance(folder, number, g.ended == "Victory")
                game.command("title @a title " + json.dumps("Campaign complete") if after is None else
                             "say " + json.dumps(f"Scenario {after} starts. Join again.")[1:-1])
                time.sleep(PAUSE)
                game.g = None                        # no save of an ended scenario
            else:
                print(f"The game ended ({g.ended}). The server stays up: type commands, Ctrl-C stops it.",
                      file=sys.stderr)               # the player can look around, as after a replay (#2051)
        while not (folder and a.play) and commands.is_alive():                   # the end of stdin stops the server; a short join keeps Ctrl-C
            commands.join(0.5)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print("Stopping the server ...", file=sys.stderr)
        state = savegame.dump(game.g) if getattr(game, "g", None) else None
        game.stop()                                  # the server writes the world when it stops
        if state:
            print(f"Saved the game: python3 game/run.py {a.world} --play --load "
                  f"{savegame.write(savegame.folder(a.world), a.world, state)}", file=sys.stderr)
    if after is not None:
        return main(argv, scenario=after)


if __name__ == "__main__":
    main()
