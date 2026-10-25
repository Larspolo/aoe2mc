#!/usr/bin/env python3
"""
In-game screenshots of a converted world with the real Minecraft client (no window, no account, no sound).

Usage:
    python3 tools/mc_shot.py WORLD OUT.png [--at X Y Z] [--look YAW PITCH] [--more X,Y,Z,YAW,PITCH ...]

The client runs in Xvfb with software rendering: Mesa OpenGL (1.21.1) or Mesa Vulkan (26.x: package
mesa-vulkan-drivers; Java 25: openjdk-25-jre-headless). A copy of the world gets a small data pack: it puts the
player in spectator mode (no hand, no hotbar), teleports it to each view and writes "aoe2mc view N" in the chat.
The script waits for that line in the client log, waits until the chunks are drawn and saves the X screen.
Without --at the camera stands 2 blocks above the spawn and looks in the spawn direction (SpawnAngle).
Yaw: 0 = south, 90 = west, 180 = north, -90 = east. Pitch: positive looks down.
Downloads (client jar, libraries) go to .cache/mc/VERSION/client/. The version comes from level.dat.
OUT.png gets the first view; the views of --more go to OUT_2.png, OUT_3.png ...
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
    if "spawn" in data:                 # 26.x: a "spawn" compound with "pos" and "yaw"
        spawn = [int(v) for v in data["spawn"]["pos"]], float(data["spawn"].get("yaw", 0.0))
    else:
        spawn = [int(data["SpawnX"]), int(data["SpawnY"]), int(data["SpawnZ"])], float(data.get("SpawnAngle", 0.0))
    return str(data["Version"]["Name"]), spawn


def add_data_pack(world, views, fmt, period):
    """A data pack that shows the views one after the other, `period` ticks each."""
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
    lines = ["scoreboard players add @a aoe2mc_t 1", "gamemode spectator @a[scores={aoe2mc_t=1}]"]
    for i, (x, y, z, yaw, pitch) in enumerate(views, 1):
        t = 40 + (i - 1) * period
        lines.append(f"execute as @a[scores={{aoe2mc_t={t}}}] run tp @s {x} {y} {z} {yaw} {pitch}")
        lines.append(f'tellraw @a[scores={{aoe2mc_t={t}}}] "aoe2mc view {i}"')
    open(os.path.join(fn, "tick.mcfunction"), "w").write("\n".join(lines) + "\n")


def free_display():
    n = 90
    while os.path.exists(f"/tmp/.X11-unix/X{n}") or os.path.exists(f"/tmp/.X{n}-lock"):
        n += 1
    return n


def shoot(world, out, views=None, version=None, size=(1280, 720), settle=8.0, timeout=240):
    """Screenshots of the views [(x, y, z, yaw, pitch)] of a world. Returns the list of written PNG files."""
    for tool in ("Xvfb", "import"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed (apt-get install xvfb imagemagick)")
    wver, (spawn, yaw) = world_version(world)
    version = version or wver
    if not views:
        views = [(spawn[0] + 0.5, spawn[1] + 2, spawn[2] + 0.5, yaw, 20)]
    cp, vj = client_files(version)
    if not version.startswith("1.") and not glob.glob("/usr/share/vulkan/icd.d/lvp_icd*.json"):
        sys.exit("Minecraft 26.x finds no GLX visual in Xvfb and needs software Vulkan: "
                 "apt-get install -y mesa-vulkan-drivers")
    java = mc_check.java_for(version)
    period = int((settle + 4) * 20)
    outs = [out] + [f"{os.path.splitext(out)[0]}_{i}.png" for i in range(2, len(views) + 1)]
    os.makedirs(os.path.join(mc_check.ROOT, ".cache"), exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.path.join(mc_check.ROOT, ".cache")) as game:
        name = "shot"
        shutil.copytree(world, os.path.join(game, "saves", name))
        add_data_pack(os.path.join(game, "saves", name), views, data_pack_format(cp[-1]), period)
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
            t0 = time.time()
            for i, path in enumerate(outs, 1):
                while f"aoe2mc view {i}" not in open(log_path, errors="replace").read():
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
    a = ap.parse_args(argv)
    _, (spawn, yaw) = world_version(a.world)
    x, y, z = a.at or (spawn[0] + 0.5, spawn[1] + 2, spawn[2] + 0.5)
    shoot(a.world, a.out, [(x, y, z, *(a.look or (yaw, 20)))] + a.more, a.version, settle=a.settle, timeout=a.timeout)

if __name__ == "__main__":
    main()
