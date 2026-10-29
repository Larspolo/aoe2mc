#!/usr/bin/env python3
"""
Load a world in a headless Minecraft server and find load errors. Also make tools/mcdata files from Mojang's reports.

Usage:
    python3 tools/mc_check.py WORLD [--version 26.3]       # exit 0: no problems, 1: problem lines (printed)
    python3 tools/mc_check.py --reports 26.3                # write tools/mcdata/26.3.json from Mojang's data

Downloads (server jars, a JDK when the installed Java is too old) go to ~/.cache/aoe2mc/mc, so that they stay
after a new clone (scripts/cloud-setup.sh fills it in the cloud snapshot). Server folders go to .cache/.
The server works on a copy of the world. It force-loads all chunks of the world, saves and stops.
"""
import argparse
import glob
import hashlib
import io
import json
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "aoe2mc", "mc")
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
DEFAULT_VERSION = "26.3"        # the default output version of aoe2mc
# Log lines with WARN or ERROR that a correct world also gives
HARMLESS = ("OFFLINE/INSECURE MODE", "make no attempt to authenticate", "possible to play without internet",
            'set "online-mode"', "Ambiguity between arguments", "Can't keep up!", "yggdrasil public key",
            "[Minecraft Services Discovery/")   # 26.x: the services host is not reachable in the sandbox
PROBLEM = re.compile(r"/(WARN|ERROR|FATAL)\]|Exception|Invalid|Unknown block|Couldn't|Failed")


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def download(url, path, sha1=None):
    if not os.path.exists(path) or sha1 and hashlib.sha1(open(path, "rb").read()).hexdigest() != sha1:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = get(url)
        if sha1 and hashlib.sha1(data).hexdigest() != sha1:
            sys.exit(f"bad checksum: {url}")
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)
    return path


def version_json(version):
    path = os.path.join(CACHE, version, "version.json")
    if not os.path.exists(path):
        entry = next((v for v in json.loads(get(MANIFEST))["versions"] if v["id"] == version), None)
        if entry is None:
            sys.exit(f"Mojang has no version {version}")
        download(entry["url"], path, entry["sha1"])
    with open(path) as f:
        return json.load(f)


def server_jar(version):
    s = version_json(version)["downloads"]["server"]
    return download(s["url"], os.path.join(CACHE, version, "server.jar"), s["sha1"])


def workdir():
    path = os.path.join(ROOT, ".cache")         # server folders: in the repository (ignored by git), not in /tmp
    if getattr(sys, "frozen", False):           # an app bundle (#1778) can be read-only (AppImage): the user cache
        path = os.path.join(os.path.dirname(CACHE), "servers")
    os.makedirs(path, exist_ok=True)
    return path


def java_major(java):
    try:
        out = subprocess.run([java, "-version"], capture_output=True, text=True).stderr
    except OSError:
        return 0
    m = re.search(r'version "(\d+)', out)
    return int(m.group(1)) if m else 0


# The java binary of a Temurin JRE in the cache, in the layout of each system (#3054)
CACHED = (("*", "bin", "java"), ("*", "Contents", "Home", "bin", "java"), ("*", "bin", "java.exe"))


def cached_javas(cache=None):
    return [j for p in CACHED for j in sorted(glob.glob(os.path.join(cache or CACHE, "jdk-*", *p)))]


def find_java(need):
    for java in [shutil.which("java")] + sorted(glob.glob("/usr/lib/jvm/*/bin/java")) + cached_javas():
        if java and java_major(java) >= need:                                       # apt installs into /usr/lib/jvm
            return java


def jre_asset(system=None, machine=None):
    """The pattern of the Temurin JRE asset of this system, or None (#3054)."""
    os_ = {"Linux": "linux", "Darwin": "mac", "Windows": "windows"}.get(system or platform.system())
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "aarch64", "aarch64": "aarch64"}.get(
        (machine or platform.machine()).lower())
    if os_ and arch:
        return rf"jre_{arch}_{os_}_hotspot_.*\." + ("zip$" if os_ == "windows" else r"tar\.gz$")


def download_jre(need, system=None, machine=None):
    """Download a Temurin JRE from the Adoptium releases on GitHub into the cache; the java binary."""
    pattern = jre_asset(system, machine)
    if pattern is None:
        raise StopIteration(f"no Temurin JRE for {platform.system()} {platform.machine()}")
    rel = json.loads(get(f"https://api.github.com/repos/adoptium/temurin{need}-binaries/releases/latest"))
    asset = next(a for a in rel["assets"] if re.search(pattern, a["name"]))
    dest = os.path.join(CACHE, f"jdk-{need}")
    print(f"downloading {asset['name']}", file=sys.stderr)
    data = io.BytesIO(get(asset["browser_download_url"]))
    if asset["name"].endswith(".zip"):
        with zipfile.ZipFile(data) as z:
            z.extractall(dest)
    else:
        with tarfile.open(fileobj=data) as t:
            t.extractall(dest, filter="data")
    return next(j for j in cached_javas() if j.startswith(dest + os.sep))


def java_for(version):
    """A java binary with the major version that the version JSON asks for (or newer)."""
    need = version_json(version).get("javaVersion", {}).get("majorVersion", 21)
    if java := find_java(need):
        return java
    # apt works in cloud sessions; api.github.com (the Adoptium download below) gives 403 there (#195).
    if hasattr(os, "geteuid") and os.geteuid() == 0 and shutil.which("apt-get"):
        print(f"installing openjdk-{need}-jre-headless with apt-get", file=sys.stderr)
        for cmd in (["apt-get", "update", "-q"], ["apt-get", "install", "-y", "-q", f"openjdk-{need}-jre-headless"]):
            if subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode:
                break
        if java := find_java(need):
            return java
    try:
        return download_jre(need)
    except (OSError, StopIteration, IndexError, tarfile.TarError, zipfile.BadZipFile) as e:
        sys.exit(f"Minecraft {version} needs Java {need}, and no Java {need} was found or installed ({e}).\n"
                 f"Install it (as root: apt-get install -y openjdk-{need}-jre-headless), or put a Java {need} "
                 f"JRE in {CACHE}/jdk-{need}/<name>/bin/java.")


def chunks(world):
    """(min cx, min cz, max cx, max cz) of the chunks in the region files."""
    xs, zs = [], []
    paths = glob.glob(os.path.join(world, "region", "r.*.*.mca")) + \
        glob.glob(os.path.join(world, "dimensions", "minecraft", "overworld", "region", "r.*.*.mca"))   # 26.1+
    for path in paths:
        rx, rz = map(int, os.path.basename(path).split(".")[1:3])
        with open(path, "rb") as f:
            head = f.read(4096)
        for i in range(1024):
            if head[4 * i:4 * i + 4] != b"\0\0\0\0":
                xs.append(rx * 32 + i % 32)
                zs.append(rz * 32 + i // 32)
    if not xs:
        sys.exit(f"no chunks in {world}")
    return min(xs), min(zs), max(xs), max(zs)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, java, jar, folder, args=(), jvm=()):
        self.lines, self.log = queue.Queue(), []
        self.p = subprocess.Popen([java, "-Xmx2G", *jvm, "-jar", jar, *args, "nogui"], cwd=folder, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.p.stdout:
            self.log.append(line.rstrip("\n"))
            self.lines.put(line)
        self.lines.put(None)

    def wait(self, pattern, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                line = self.lines.get(timeout=1)
            except queue.Empty:
                continue
            if line is None:
                raise RuntimeError("the server stopped")
            if re.search(pattern, line):
                return line
        raise TimeoutError(f"no '{pattern}' after {timeout} s")

    def send(self, command):
        self.p.stdin.write(command + "\n")
        self.p.stdin.flush()


def problems(log):
    """Problem log entries. An entry is a "[time] [thread/LEVEL]" line with its stack trace lines."""
    entries = []
    for line in log:
        if line.startswith("[") or not entries:
            entries.append([line])
        else:
            entries[-1].append(line)
    return ["\n".join(e) for e in entries
            if any(PROBLEM.search(line) for line in e) and not any(h in e[0] for h in HARMLESS)]


def check(world, version=DEFAULT_VERSION, timeout=300, keep=None):
    """Load all chunks of the world in a server. Returns (problem lines, full log).
    keep: copy the world that the server saved to this folder (to read the NBT as Minecraft wrote it)."""
    jar, java = server_jar(version), java_for(version)
    x0, z0, x1, z1 = chunks(world)
    with tempfile.TemporaryDirectory(dir=workdir()) as folder:
        shutil.copytree(world, os.path.join(folder, "world"))
        with open(os.path.join(folder, "eula.txt"), "w") as f:
            f.write("eula=true\n")
        with open(os.path.join(folder, "server.properties"), "w") as f:
            f.write(f"online-mode=false\nlevel-name=world\nserver-port={free_port()}\nspawn-protection=0\n"
                    "max-tick-time=-1\nsync-chunk-writes=false\nenable-query=false\nenable-rcon=false\n")
        s = Server(java, jar, folder)
        try:
            s.wait(r"\]: Done \(", timeout)
            for cx in range(x0, x1 + 1, 16):         # forceload takes at most 256 chunks per command
                for cz in range(z0, z1 + 1, 16):
                    s.send(f"forceload add {cx * 16} {cz * 16} {min(cx + 15, x1) * 16} {min(cz + 15, z1) * 16}")
            n = (x1 - x0 + 1) * (z1 - z0 + 1)
            s.send("worldborder get")              # the log shows the width of the vanilla border (#172)
            s.send(f"say forceload sent for {n} chunks")
            s.wait(r"forceload sent for", timeout)
            time.sleep(5 + n * 0.02)                 # chunks and entities load in other threads
            s.send("save-all flush")
            s.wait(r"Saved the game", timeout)
            s.send("stop")
            s.p.wait(timeout)
            if keep:
                shutil.copytree(os.path.join(folder, "world"), keep, dirs_exist_ok=True)
        except (RuntimeError, TimeoutError) as e:
            s.log.append(f"[mc_check/ERROR]: {e}")
        finally:
            if s.p.poll() is None:
                s.p.kill()
                s.p.wait()
    return problems(s.log), s.log


def reports(version):
    """Write tools/mcdata/VERSION.json (format of fetch_mcdata.py) from Mojang's data reports."""
    jar, java = server_jar(version), java_for(version)
    with tempfile.TemporaryDirectory(dir=workdir()) as folder:
        subprocess.run([java, "-DbundlerMainClass=net.minecraft.data.Main", "-jar", jar, "--reports",
                        "--output", "gen"], cwd=folder, check=True, capture_output=True)
        with open(os.path.join(folder, "gen", "reports", "blocks.json")) as f:
            raw = json.load(f)
        with open(os.path.join(folder, "gen", "reports", "registries.json")) as f:
            registries = json.load(f)
    blocks = {k.removeprefix("minecraft:"): v.get("properties", {}) for k, v in raw.items()}
    entities = sorted(k.removeprefix("minecraft:") for k in registries["minecraft:entity_type"]["entries"])
    sounds = sorted(k.removeprefix("minecraft:") for k in registries["minecraft:sound_event"]["entries"])
    # Biomes are data, not a registry report: read their file names in the server jar inside the bundle
    with zipfile.ZipFile(jar) as z:
        inner = next(n for n in z.namelist() if n.startswith("META-INF/versions/") and n.endswith(".jar"))
        with zipfile.ZipFile(io.BytesIO(z.read(inner))) as zz:
            biomes = sorted(n.split("/")[-1][:-5] for n in zz.namelist()
                            if n.startswith("data/minecraft/worldgen/biome/") and n.endswith(".json"))
    data = {"version": version, "source": {k: f"mojang/{version}" for k in ("blocks", "entities", "biomes", "sounds")},
            "blocks": blocks, "entities": entities, "biomes": biomes, "sounds": sounds}
    path = os.path.join(ROOT, "tools", "mcdata", f"{version}.json")
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)
    print(f"Wrote {path}: {len(blocks)} blocks, {len(entities)} entities, {len(biomes)} biomes, {len(sounds)} sounds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("world", nargs="?", help="world folder to load")
    ap.add_argument("--version", default=DEFAULT_VERSION, help="Minecraft version (default %(default)s)")
    ap.add_argument("--reports", metavar="VERSION", help="write tools/mcdata/VERSION.json from Mojang's reports")
    ap.add_argument("--log", help="write the full server log to this file")
    ap.add_argument("--keep", metavar="DIR", help="copy the world as the server saved it to DIR")
    a = ap.parse_args(argv)
    if a.reports:
        reports(a.reports)
        return 0
    if not a.world:
        ap.error("give a WORLD or --reports VERSION")
    bad, log = check(a.world, a.version, keep=a.keep)
    if a.log:
        with open(a.log, "w") as f:
            f.write("\n".join(log) + "\n")
    if bad:
        print(f"{len(bad)} problem lines in the server log:")
        print("\n".join(bad[:50]))
        return 1
    print(f"OK: Minecraft {a.version} loaded {a.world} without problems ({len(log)} log lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
