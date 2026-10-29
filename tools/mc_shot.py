#!/usr/bin/env python3
"""
In-game screenshots of a converted world with the real Minecraft client (no window, no account, no sound).

Usage:
    python3 tools/mc_shot.py WORLD OUT.png [--at X Y Z] [--look YAW PITCH] [--more X,Y,Z,YAW,PITCH ...]

The client runs in Xvfb with software rendering: Mesa Vulkan (package mesa-vulkan-drivers; Java 25:
openjdk-25-jre-headless). A copy of the world gets a small data pack: it puts the player in spectator mode (no hand, no hotbar), teleports it to each view and writes "aoe2mc view N" in the chat.
The script waits for that line in the client log, waits until the chunks are drawn and saves the X screen.
Without --at the camera stands 2 blocks above the spawn and looks in the spawn direction (the yaw of the spawn).
Yaw: 0 = south, 90 = west, 180 = north, -90 = east. Pitch: positive looks down.
Downloads (client jar, libraries) go to .cache/mc/VERSION/client/. The version comes from level.dat.
OUT.png gets the first view; the views of --more go to OUT_2.png, OUT_3.png ...
Client(port) joins the same client to a server on 127.0.0.1 (the Paper server of game/run.py, #627): a test sees
and clicks the game as a player (shot(), click(), key(): xdotool on the X screen).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mc_check  # noqa: E402

OPTIONS = {"onboardAccessibility": "false",    # else the first-start screen stops --quickPlaySingleplayer
           "pauseOnLostFocus": "false", "tutorialStep": "none", "renderDistance": "8", "simulationDistance": "5",
           "soundCategory_master": "0.0", "narrator": "0", "joinedFirstServer": "true", "skipMultiplayerWarning": "true",
           "chatScale": "0.0"}     # the chat is not drawn, but the "view N" lines go to the log


def allowed(lib):
    """The rules of a library entry for Linux."""
    ok = not lib.get("rules")
    for r in lib.get("rules", []):
        if r.get("os", {}).get("name") in (None, "linux"):
            ok = r["action"] == "allow"
    return ok


def client_files(version):
    """Download the client jar and the Linux libraries. Returns the class path."""
    vj = mc_check.version_json(version)
    base = os.path.join(mc_check.CACHE, version, "client")
    cp = []
    for lib in vj["libraries"]:
        a = lib.get("downloads", {}).get("artifact")
        if a and allowed(lib):
            cp.append(mc_check.download(a["url"], os.path.join(base, "libraries", a["path"]), a["sha1"]))
    c = vj["downloads"]["client"]
    cp.append(mc_check.download(c["url"], os.path.join(base, "client.jar"), c["sha1"]))
    ai = vj["assetIndex"]
    index = mc_check.download(ai["url"], os.path.join(base, "assets", "indexes", ai["id"] + ".json"), ai["sha1"])
    placeholder_images(os.path.join(base, "assets"), index)
    return cp, vj


def placeholder_images(assets, index):
    """The asset objects (sounds, title panorama) are on resources.download.minecraft.net, which the sandbox blocks.
    The textures of the world are in client.jar. 26.x stops when the panorama is missing: put a 1 x 1 PNG there."""
    from PIL import Image
    for name, o in json.load(open(index))["objects"].items():
        path = os.path.join(assets, "objects", o["hash"][:2], o["hash"])
        if name.endswith(".png") and not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            Image.new("RGBA", (1, 1)).save(path, "PNG")


def data_pack_format(client_jar):
    with zipfile.ZipFile(client_jar) as z:
        pv = json.loads(z.read("version.json"))["pack_version"]
    return pv.get("data", pv.get("data_major"))


def world_version(world):
    from nbtlib import load
    data = load(os.path.join(world, "level.dat"))["Data"]
    spawn = [int(v) for v in data["spawn"]["pos"]], float(data["spawn"].get("yaw", 0.0))    # 26.x: "pos", "yaw"
    return str(data["Version"]["Name"]), spawn


def add_data_pack(world, views, fmt, period, player=False):
    """A data pack that shows the views one after the other, `period` ticks each. player: adventure mode, not
    spectator (a spectator sees invisible mobs, #636), and a teleport in each tick of a view (else the player falls)."""
    root = os.path.join(world, "datapacks", "aoe2mc_shot")
    fn = os.path.join(root, "data", "aoe2mc_shot", "function")
    tags = os.path.join(root, "data", "minecraft", "tags", "function")
    os.makedirs(fn, exist_ok=True)
    os.makedirs(tags, exist_ok=True)
    meta = {"pack": {"description": "aoe2mc screenshots", "pack_format": fmt, "min_format": fmt, "max_format": fmt}}
    json.dump(meta, open(os.path.join(root, "pack.mcmeta"), "w"))
    json.dump({"values": ["aoe2mc_shot:load"]}, open(os.path.join(tags, "load.json"), "w"))
    json.dump({"values": ["aoe2mc_shot:tick"]}, open(os.path.join(tags, "tick.json"), "w"))
    open(os.path.join(fn, "load.mcfunction"), "w").write("scoreboard objectives add aoe2mc_t dummy\n")
    mode = "adventure" if player else "spectator"
    lines = ["scoreboard players add @a aoe2mc_t 1", f"gamemode {mode} @a[scores={{aoe2mc_t=1}}]"]
    for i, (x, y, z, yaw, pitch) in enumerate(views, 1):
        t = 40 + (i - 1) * period
        span = f"{t}..{'' if i == len(views) else t + period - 1}" if player else t
        lines.append(f"execute as @a[scores={{aoe2mc_t={span}}}] run tp @s {x} {y} {z} {yaw} {pitch}")
        lines.append(f'tellraw @a[scores={{aoe2mc_t={t}}}] "aoe2mc view {i}"')
    open(os.path.join(fn, "tick.mcfunction"), "w").write("\n".join(lines) + "\n")


def free_display():
    n = 90
    while os.path.exists(f"/tmp/.X11-unix/X{n}") or os.path.exists(f"/tmp/.X{n}-lock"):
        n += 1
    return n


def shoot(world, out, views=None, version=None, size=(1280, 720), settle=8.0, timeout=240, player=False):
    """Screenshots of the views [(x, y, z, yaw, pitch)] of a world. Returns the list of written PNG files.
    player: the view of a player in adventure mode (with hand and hotbar), not of a spectator."""
    for tool in ("Xvfb", "import"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed (apt-get install xvfb imagemagick)")
    wver, (spawn, yaw) = world_version(world)
    version = version or wver
    if not views:
        views = [(spawn[0] + 0.5, spawn[1] + 2, spawn[2] + 0.5, yaw, 20)]
    cp, vj = client_files(version)
    if not glob.glob("/usr/share/vulkan/icd.d/lvp_icd*.json"):
        sys.exit("Minecraft 26.x finds no GLX visual in Xvfb and needs software Vulkan: "
                 "apt-get install -y mesa-vulkan-drivers")
    java = mc_check.java_for(version)
    period = int((settle + 4) * 20)
    outs = [out] + [f"{os.path.splitext(out)[0]}_{i}.png" for i in range(2, len(views) + 1)]
    os.makedirs(os.path.join(mc_check.ROOT, ".cache"), exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.path.join(mc_check.ROOT, ".cache")) as game:
        name = "shot"
        shutil.copytree(world, os.path.join(game, "saves", name))
        add_data_pack(os.path.join(game, "saves", name), views, data_pack_format(cp[-1]), period, player)
        with open(os.path.join(game, "options.txt"), "w") as f:
            f.writelines(f"{k}:{v}\n" for k, v in OPTIONS.items())
        disp = free_display()
        env = dict(os.environ, DISPLAY=f":{disp}", LIBGL_ALWAYS_SOFTWARE="1")
        xvfb = subprocess.Popen(["Xvfb", f":{disp}", "-screen", "0", f"{size[0]}x{size[1]}x24"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log_path = os.path.join(game, "client.log")
        log = open(log_path, "w")
        client = None
        try:
            time.sleep(1)
            base = os.path.join(mc_check.CACHE, version, "client")
            client = subprocess.Popen(
                [java, "-Xmx2G", "-cp", ":".join(cp), vj["mainClass"], "--username", "aoe2mc", "--version", version,
                 "--gameDir", game, "--assetsDir", os.path.join(base, "assets"), "--assetIndex", vj["assetIndex"]["id"],
                 "--uuid", "00000000-0000-0000-0000-000000000001", "--accessToken", "0", "--userType", "legacy",
                 "--width", str(size[0]), "--height", str(size[1]), "--quickPlaySingleplayer", name],
                cwd=game, env=env, stdout=log, stderr=subprocess.STDOUT)
            t0, loaded, warned = time.time(), None, not shutil.which("xdotool")
            for i, path in enumerate(outs, 1):
                while f"aoe2mc view {i}" not in (text := open(log_path, errors="replace").read()):
                    # A timeline file (--fog) stops the world at "Worlds using Experimental Settings" (#1641): Tab,
                    # Tab and Enter press its second button "I Know What I'm Doing!". In the game the keys do nothing.
                    loaded = loaded or ("Loaded" in text and "advancements" in text and time.time())
                    if not warned and loaded and time.time() - loaded > 15:
                        for k in ("Tab", "Tab", "Return"):
                            subprocess.run(["xdotool", "key", k], env=env)
                            time.sleep(0.5)
                        warned = True
                    if client.poll() is not None or time.time() - t0 > timeout:
                        shutil.copy(log_path, out + ".log")
                        subprocess.run(["import", "-window", "root", out], env=env)   # the screen that stops it
                        sys.exit(f"the client did not reach view {i} ({time.time() - t0:.0f} s): see {out} "
                                 f"and {out}.log")
                    time.sleep(0.5)
                time.sleep(settle)          # the chunks around the new position are drawn
                subprocess.run(["import", "-window", "root", path], env=env, check=True)
                print(f"Wrote {path} ({time.time() - t0:.0f} s)")
        finally:
            for p in (client, xvfb):
                if p and p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(10)
                    except subprocess.TimeoutExpired:
                        p.kill()
            log.close()
    return outs


def forget(world, name):
    """Delete the saved files of the player name in the world (playerdata, advancements, stats; #3831): each start is a
    living player with full health (#3418: a dead player was saved and later runs started dead). An offline server
    names the player by the UUID of "OfflinePlayer:<name>", as Java's UUID.nameUUIDFromBytes."""
    uid = str(uuid.UUID(bytes=hashlib.md5(f"OfflinePlayer:{name}".encode()).digest(), version=3))
    for root, _, files in os.walk(world):
        for f in files:
            if f.startswith(uid):
                os.remove(os.path.join(root, f))


class Client:
    """The client as player "aoe2mc" on the server at 127.0.0.1:port (online-mode=false), in Xvfb. A context manager:
    the client is in the world when wait_join() returns (or the test sees the player in "list").
    chat: draw the chat (OPTIONS hides it), for a screenshot of a message (#780)."""

    SCALE = 3                       # GUI scale: slot() needs a fixed one

    def __init__(self, port, version, size=(1280, 720), name="aoe2mc", chat=False, world=None):
        for tool in ("Xvfb", "import", "xdotool"):
            if not shutil.which(tool):
                sys.exit(f"{tool} is not installed (apt-get install xvfb imagemagick xdotool)")
        self.port, self.version, self.size, self.name, self.chat = port, version, size, name, chat
        self.client = self.xvfb = self.log = None
        if world:
            forget(world, name)

    def __enter__(self):
        cp, vj = client_files(self.version)
        os.makedirs(os.path.join(mc_check.ROOT, ".cache"), exist_ok=True)
        self.game = tempfile.mkdtemp(dir=os.path.join(mc_check.ROOT, ".cache"))
        opts = OPTIONS | {"guiScale": self.SCALE} | ({"chatScale": "1.0"} if self.chat else {})
        with open(os.path.join(self.game, "options.txt"), "w") as f:
            f.writelines(f"{k}:{v}\n" for k, v in opts.items())
        disp = free_display()
        self.env = dict(os.environ, DISPLAY=f":{disp}", LIBGL_ALWAYS_SOFTWARE="1")
        self.xvfb = subprocess.Popen(["Xvfb", f":{disp}", "-screen", "0", f"{self.size[0]}x{self.size[1]}x24"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.log_path = os.path.join(self.game, "client.log")
        self.log = open(self.log_path, "w")
        time.sleep(1)
        base = os.path.join(mc_check.CACHE, self.version, "client")
        self.client = subprocess.Popen(
            [mc_check.java_for(self.version), "-Xmx2G", "-cp", ":".join(cp), vj["mainClass"], "--username", self.name,
             "--version", self.version, "--gameDir", self.game, "--assetsDir", os.path.join(base, "assets"),
             "--assetIndex", vj["assetIndex"]["id"], "--uuid", "00000000-0000-0000-0000-000000000001",
             "--accessToken", "0", "--userType", "legacy", "--width", str(self.size[0]), "--height", str(self.size[1]),
             "--quickPlayMultiplayer", f"127.0.0.1:{self.port}"],
            cwd=self.game, env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        return self

    def __exit__(self, *exc):
        for p in (self.client, self.xvfb):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()
        if self.log:
            self.log.close()
        shutil.rmtree(self.game, ignore_errors=True)

    def text(self):
        return open(self.log_path, errors="replace").read()

    def wait_join(self, joined, timeout=240):
        """Wait until joined() is true (for example: the name is in the "list" of the server)."""
        t0 = time.time()
        while not joined():
            if self.client.poll() is not None or time.time() - t0 > timeout:
                raise RuntimeError(f"the client did not join ({time.time() - t0:.0f} s): {self.text()[-2000:]}")
            time.sleep(1)

    def shot(self, path):
        subprocess.run(["import", "-window", "root", path], env=self.env, check=True)
        return path

    def xdo(self, *args):
        subprocess.run(["xdotool", *map(str, args)], env=self.env, check=True)

    def click(self, x, y, button=1):
        """A mouse click at the screen pixel (x, y): in an open inventory the pointer is free (no grab)."""
        self.xdo("mousemove", x, y)
        time.sleep(0.3)
        self.xdo("click", button)

    def slot(self, i, rows):
        """The screen pixel of the middle of slot i of an open chest menu with rows rows: the vanilla container
        screen is 176 x (114 + 18 rows) GUI pixels in the middle of the screen, slots of 18 from (8, 18)."""
        w, h = self.size[0] // self.SCALE, self.size[1] // self.SCALE
        left, top = (w - 176) // 2, (h - 114 - 18 * rows) // 2
        return (left + 8 + i % 9 * 18 + 8) * self.SCALE, (top + 18 + i // 9 * 18 + 8) * self.SCALE

    def key(self, name):
        self.xdo("key", name)

    def place(self, game, x, y, z, yaw=0, pitch=20, wait=15.0):
        """Teleport the player onto a 3 x 3 stone platform under (x, y, z) and wait until the client has loaded the
        chunks (#3831): after a long tp the first image was only sky (#3370), and a player fell off (#3400)."""
        game.command(f"fill {x - 1} {y - 1} {z - 1} {x + 1} {y - 1} {z + 1} minecraft:stone")
        game.command(f"tp {self.name} {x + 0.5} {y} {z + 0.5} {yaw} {pitch}")
        time.sleep(wait)

    @staticmethod
    def health(game, target):
        """The Health of a mob by its UUID, selector or tag (#3831), or None when no such mob is there."""
        sel = target if "-" in target or target.startswith("@") else f"@e[tag={target},limit=1]"
        m = re.search(r"has the following entity data: ([-0-9.]+)f?", game.command(f"data get entity {sel} Health"))
        return float(m.group(1)) if m else None

    def pick(self, g, want, dists=(3, 5, 7), wait=2.0):
        """Aim at want (a unit UUID, or the footprint rect of an own building) of the Gather g and right click it
        (#2963). Try each stand point of aims() and click only when g.target() picks want: a ray past a unit can hit
        the building behind it (#2945). Return the stand point, or None when no side hits it."""
        if isinstance(want, str):
            if not (feet := g.pos(want)):
                return None
            mid, ground = (feet[0], feet[1] + 1.0, feet[2]), feet[1]   # the body of the unit, not its feet
        else:
            ground = g.pos(self.name)[1]
            mid = ((want[0] + want[1]) / 2, ground + 1.62, (want[2] + want[3]) / 2)
        for stand, face in aims(mid, dists, ground):
            g.command(f"tp {self.name} {stand[0]:.2f} {stand[1]:.2f} {stand[2]:.2f} facing "
                      f"{face[0]:.2f} {face[1]:.2f} {face[2]:.2f}")
            time.sleep(0.5)
            if (look := g.look(self.name)) and hits(g.target(*look, g.positions(sorted(g.pickable()))), want):
                self.click(self.size[0] // 2, self.size[1] // 2, button=3)
                time.sleep(wait)                                       # gather.HOLD: one click, no selection box
                return stand
        return None


def aims(mid, dists=(3, 5, 7), feet=None):
    """(stand feet, facing point) for each distance and 8 directions around mid, the point that the eye ray must
    hit. tp ... facing aims the ray of the feet, so the facing point is 1.62 below mid (#1666). feet: the ground
    level of the stand; feet in a block lose the sneak pose (#3884). Default: the eye at the height of mid."""
    x, y, z = mid
    face, sy = (x, y - 1.62, z), y - 1.62 if feet is None else feet
    return [((x + d * dx, sy, z + d * dz), face) for d in dists
            for dx, dz in ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))]


def hits(target, want):
    """True when the target of Gather.target() is want: a UUID, or the rect of a building."""
    return bool(target) and target[1] == (want if isinstance(want, str) else tuple(want))


def view_spec(v):
    try:
        x, y, z, yaw, pitch = (float(t) for t in v.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{v!r} is not X,Y,Z,YAW,PITCH") from None
    return x, y, z, yaw, pitch


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("out", help="PNG file of the first view")
    ap.add_argument("--at", nargs=3, type=float, metavar=("X", "Y", "Z"), help="camera position (default: above the spawn)")
    ap.add_argument("--look", nargs=2, type=float, metavar=("YAW", "PITCH"), default=None,
                    help="camera direction (default: the spawn angle, pitch 20)")
    ap.add_argument("--more", type=view_spec, action="append", default=[], metavar="X,Y,Z,YAW,PITCH",
                    help="one more view (can be repeated)")
    ap.add_argument("--version", help="client version (default: the version in level.dat)")
    ap.add_argument("--settle", type=float, default=8.0, help="seconds to wait for the chunks of a view (default 8)")
    ap.add_argument("--timeout", type=float, default=240, help="seconds until the last view (default 240)")
    ap.add_argument("--player", action="store_true",
                    help="adventure mode, not spectator: a spectator sees invisible mobs (with hand and hotbar)")
    a = ap.parse_args(argv)
    _, (spawn, yaw) = world_version(a.world)
    x, y, z = a.at or (spawn[0] + 0.5, spawn[1] + 2, spawn[2] + 0.5)
    shoot(a.world, a.out, [(x, y, z, *(a.look or (yaw, 20)))] + a.more, a.version, settle=a.settle, timeout=a.timeout,
          player=a.player)

if __name__ == "__main__":
    main()
