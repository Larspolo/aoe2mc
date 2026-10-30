#!/usr/bin/env python3
"""
Measure the cost of the resource pack of --resource-pack (#2747): its size, its download time from a local HTTP
server, and the frame time of the real client on the same view with and without the pack.

Usage:
    python3 tools/pack_cost.py [--scenario battle] [--seconds 10] [--out DIR]

The tool converts the scenario (`tools/scenarios.py`) twice, without and with --resource-pack. For each world it
starts the real client in single player (`mc_shot`: Xvfb, software Vulkan), puts the spectator 12 blocks above the
spawn, looking down at the units, and starts the vanilla debug profiler (F3 + L) for `--seconds`. The profiler writes
the time of each frame into `debug/profiling/*.zip` (`client/metrics/ticking.csv`, column `ticktime`, nanoseconds:
the client profiler counts one tick per frame, `profiling.txt`: "frame(N/1)"). The tool prints the
median and P95 frame time of both worlds and the difference, and saves the view as WORLD.png. Under Xvfb the client draws in software: only the
difference counts, not the absolute value. The server cost: `tools/tick_cost.py --world WORLD` on both worlds.
"""
import argparse
import contextlib
import csv
import glob
import http.server
import io
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]
import mc_check  # noqa: E402
import mc_shot  # noqa: E402


def download_seconds(path):
    """Seconds to fetch the file at path from a local HTTP server (the game program serves the pack so, #2740)."""
    folder, name = os.path.split(path)

    class handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a):
            super().__init__(*a, directory=folder)

        def log_message(self, *a):
            pass
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        t0 = time.time()
        urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/{name}").read()
        dt = time.time() - t0
        srv.shutdown()
    return dt


def frame_times(world, seconds=10, settle=15.0, timeout=300):
    """The frame times (ms) of the vanilla profiler (F3 + L) of the client on the view 12 blocks above the spawn."""
    version, (spawn, yaw) = mc_shot.world_version(world)
    cp, vj = mc_shot.client_files(version)
    views = [(spawn[0] + 0.5, spawn[1] + 12, spawn[2] + 0.5, yaw, 45)]
    with tempfile.TemporaryDirectory(dir=os.path.join(mc_check.ROOT, ".cache")) as game:
        shutil.copytree(world, os.path.join(game, "saves", "cost"))
        mc_shot.add_data_pack(os.path.join(game, "saves", "cost"), views, mc_shot.data_pack_format(cp[-1]), 100000)
        with open(os.path.join(game, "options.txt"), "w") as f:
            f.writelines(f"{k}:{v}\n" for k, v in mc_shot.OPTIONS.items())
        disp = mc_shot.free_display()
        env = dict(os.environ, DISPLAY=f":{disp}", LIBGL_ALWAYS_SOFTWARE="1")
        xvfb = subprocess.Popen(["Xvfb", f":{disp}", "-screen", "0", "1280x720x24"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log_path = os.path.join(game, "client.log")
        client = None
        try:
            time.sleep(1)
            base = os.path.join(mc_check.CACHE, version, "client")
            client = subprocess.Popen(
                [mc_check.java_for(version), "-Xmx2G", "-cp", ":".join(cp), vj["mainClass"], "--username", "aoe2mc",
                 "--version", version, "--gameDir", game, "--assetsDir", os.path.join(base, "assets"),
                 "--assetIndex", vj["assetIndex"]["id"], "--uuid", "00000000-0000-0000-0000-000000000001",
                 "--accessToken", "0", "--userType", "legacy", "--width", "1280", "--height", "720",
                 "--quickPlaySingleplayer", "cost"],
                cwd=game, env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)
            t0 = time.time()
            while "aoe2mc view 1" not in open(log_path, errors="replace").read():
                if client.poll() is not None or time.time() - t0 > timeout:
                    sys.exit(f"the client did not reach the view: {open(log_path, errors='replace').read()[-2000:]}")
                time.sleep(0.5)
            time.sleep(settle)                                         # the chunks and the units are drawn
            subprocess.run(["import", "-window", "root", world + ".png"], env=env, check=True)   # is the pack on?
            subprocess.run(["xdotool", "key", "F3+l"], env=env, check=True)
            time.sleep(seconds)
            subprocess.run(["xdotool", "key", "F3+l"], env=env, check=True)
            while not (found := glob.glob(os.path.join(game, "debug", "profiling", "*.zip"))):
                if time.time() - t0 > timeout + seconds:
                    sys.exit(f"the profiler wrote no file: {open(log_path, errors='replace').read()[-2000:]}")
                time.sleep(0.5)
            time.sleep(2)
            with zipfile.ZipFile(found[0]) as z:
                rows = list(csv.reader(io.TextIOWrapper(z.open("client/metrics/ticking.csv"))))
            shutil.copy(found[0], os.path.join(os.path.dirname(world), os.path.basename(world) + "-profile.zip"))
        finally:
            for p in (client, xvfb):
                if p and p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(10)
                    except subprocess.TimeoutExpired:
                        p.kill()
    cols = [i for i, h in enumerate(rows[0]) if h == "ticktime"]
    if not cols:
        sys.exit(f"no ticktime column in client/metrics/ticking.csv: {rows[0]}")
    col = cols[0]
    return [float(r[col]) / 1e6 for r in rows[1:] if r[col]]


def p95(v):
    return sorted(v)[int(0.95 * (len(v) - 1))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="battle", help="a kind of tools/scenarios.py (default battle)")
    ap.add_argument("--seconds", type=float, default=10, help="profiler time per world (default 10)")
    ap.add_argument("--out", help="keep the two worlds in this folder")
    a = ap.parse_args(argv)
    import scenarios

    import aoe2mc
    folder = a.out or tempfile.mkdtemp(dir=os.path.join(mc_check.ROOT, ".cache"))
    os.makedirs(folder, exist_ok=True)
    src = os.path.join(folder, f"{a.scenario}.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        scenarios.MAKERS[a.scenario](src)
        for name, pack in (("without", False), ("with", True)):
            aoe2mc.main([src, os.path.join(folder, name)] + ["--resource-pack"] * pack)
    zip_path = os.path.join(folder, "with", "resourcepacks", "resources.zip")
    print(f"resources.zip: {os.path.getsize(zip_path) / 1e6:.1f} MB, local HTTP download {download_seconds(zip_path):.2f} s")
    res = {}
    for name in ("without", "with"):
        ms = frame_times(os.path.join(folder, name), a.seconds)
        res[name] = statistics.median(ms), p95(ms)
        print(f"{name} pack: {len(ms)} frames, median {res[name][0]:.1f} ms, P95 {res[name][1]:.1f} ms")
    (m0, q0), (m1, q1) = res["without"], res["with"]
    print(f"frame time with the pack: median {(m1 - m0) / m0 * 100:+.0f} %, P95 {(q1 - q0) / q0 * 100:+.0f} % "
          "(software rendering under Xvfb: only the difference counts)")
    if not a.out:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    main()
