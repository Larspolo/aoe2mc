"""Walk the installer path of docs/PLAYTEST.md (sections 2 and 3) with the local bundle and the real client (#5885).

Usage: python3 tools/installer_check.py OUT [--dist out/dist/aoe2mc] [--actions "key:1;btn:1;shot:select"]

It builds the bundle when --dist has none (docs/packaging.md, "Build a bundle locally"), runs each command of the
installer path in OUT/run (a folder with no checkout), joins each game with mc_shot.Client, does the actions, stops
the game with Ctrl-C and writes OUT/steps.md and the screenshots OUT/<game>-<name>.png.
Actions (";" between them): key:NAME, btn:N (a click with no move: the game grabs the pointer), look:dx,dy,
hold:N,SECONDS,dx,dy (a drag with a screenshot during it), slot:I,ROWS (a click on slot I of an open chest menu),
type:TEXT (a chat line), shot:NAME, sleep:SECONDS.
Pitfall: the local bundle has no release.json, so the server offers no resource pack (docs/minecraft-versions.md).
"""
import argparse
import os
import re
import signal
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

VERSION = "26.3"
PORT = re.compile(r"Join the server localhost:(\d+)")
SAVED = re.compile(r"Saved the game: (.+)")
JOINED = re.compile(r"(\w{1,16}) joined the game|\[CHAT\]")
ARGS = {"key": 1, "btn": 1, "look": 2, "hold": 4, "slot": 2, "type": 1, "shot": 1, "sleep": 1}
STEPS = [("aoe2mc", "--random-map arabia --seed 1 OUTWorld"), ("aoe2mc-game", "OUTWorld --play --tutorial"),
         ("aoe2mc", "--random-map arabia --seed 1 BotWorld"),
         ("aoe2mc-game", "BotWorld --play --bot --ai-difficulty easiest")]


def parse_actions(text):
    """'key:1;look:10,-5' -> [("key", ["1"]), ("look", ["10", "-5"])]; a bad action raises ValueError."""
    out = []
    for item in filter(None, (s.strip() for s in text.split(";"))):
        name, _, rest = item.partition(":")
        if name not in ARGS:
            raise ValueError(f"unknown action {name!r} (known: {', '.join(ARGS)})")
        args = [rest] if name == "type" else rest.split(",")
        if len(args) != ARGS[name] or not all(args):
            raise ValueError(f"{item!r}: {name} takes {ARGS[name]} argument(s)")
        out.append((name, args))
    return out


def find_port(text):
    m = PORT.search(text)
    return int(m.group(1)) if m else None


def find_saved(text):
    m = SAVED.search(text)
    return m.group(1).strip() if m else None


def act(client, actions, out, tag):
    shots = []
    for name, a in actions:
        if name == "key":
            client.key(a[0])
        elif name == "btn":
            client.xdo("click", a[0])
        elif name == "look":
            client.xdo("mousemove_relative", "--", a[0], a[1])
        elif name == "hold":
            client.xdo("mousedown", a[0])
            client.xdo("mousemove_relative", "--", a[2], a[3])
            time.sleep(float(a[1]) / 2)
            shots.append(client.shot(os.path.join(out, f"{tag}-hold.png")))
            time.sleep(float(a[1]) / 2)
            client.xdo("mouseup", a[0])
        elif name == "slot":
            client.click(*client.slot(int(a[0]), int(a[1])))
        elif name == "type":
            client.key("t")
            time.sleep(0.5)
            client.xdo("type", "--delay", "40", a[0])
            client.key("Return")
        elif name == "shot":
            shots.append(client.shot(os.path.join(out, f"{tag}-{a[0]}.png")))
        elif name == "sleep":
            time.sleep(float(a[0]))
        time.sleep(1)
    return shots


def game_step(cmd, cwd, out, tag, actions, timeout):
    """Start the game, join it with the client, do the actions, Ctrl-C: (rc, port, joined, saved line, shots)."""
    import mc_shot
    log = []
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    threading.Thread(target=lambda: [log.append(x) for x in p.stdout], daemon=True).start()
    t0, port, joined, shots = time.time(), None, False, []
    while port is None and p.poll() is None and time.time() - t0 < timeout:
        port = find_port("".join(log))
        time.sleep(1)
    if port:
        with mc_shot.Client(port, VERSION, chat=True) as client:
            try:
                client.wait_join(lambda: bool(JOINED.search("".join(log) + client.text())), timeout)
                joined = True
                time.sleep(10)                  # the tutorial and the boss bar start after the join
                shots = act(client, actions, out, tag)
                shots.append(client.shot(os.path.join(out, f"{tag}-end.png")))
            except RuntimeError as e:
                log.append(f"[installer_check] {e}\n")
    if p.poll() is None:
        os.killpg(p.pid, signal.SIGINT)
    try:
        rc = p.wait(180)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        rc = p.wait()
    time.sleep(1)
    text = "".join(log)
    with open(os.path.join(out, f"{tag}.log"), "w") as f:
        f.write(text)
    return rc, port, joined, find_saved(text), shots


def build(dist):
    if os.path.exists(os.path.join(dist, "aoe2mc-game")):
        return
    plugin = os.path.join(ROOT, "game", "plugin")
    if not os.path.exists(os.path.join(plugin, "aoe2mc-plugin.jar")):
        subprocess.run(["./gradlew", "--no-daemon", "-q", "jar"], cwd=plugin, check=True)
        subprocess.run(["cp", "build/libs/aoe2mc-plugin.jar", "."], cwd=plugin, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "packaging/aoe2mc.spec",
                    "--distpath", os.path.dirname(dist), "--workpath", os.path.join(ROOT, "out", "build")],
                   cwd=ROOT, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--dist", default=os.path.join(ROOT, "out", "dist", "aoe2mc"))
    ap.add_argument("--actions", default="shot:join", help="the inputs after each join")
    ap.add_argument("--timeout", type=int, default=600, help="seconds to wait for the server and the join")
    a = ap.parse_args(argv)
    actions = parse_actions(a.actions)
    out = os.path.abspath(a.out)
    run = os.path.join(out, "run")
    os.makedirs(run, exist_ok=True)
    dist = os.path.abspath(a.dist)
    build(dist)
    rows = ["| Command | Exit code | Join | Saved game |", "|---|---|---|---|"]
    for prog, args in STEPS:
        cmd = [os.path.join(dist, prog), *args.split()]
        world = args.split()[-1] if prog == "aoe2mc" else args.split()[0]
        if prog == "aoe2mc":
            r = subprocess.run(cmd, cwd=run, capture_output=True, text=True)
            ok = os.path.exists(os.path.join(run, world, "level.dat"))
            rows.append(f"| `{prog} {args}` | {r.returncode} | - | - |" + ("" if ok else " (no level.dat)"))
        else:
            rc, port, joined, saved, shots = game_step(cmd, run, out, world, actions, a.timeout)
            join = f"localhost:{port} {'joined' if joined else 'NOT joined'}" if port else "no port"
            rows.append(f"| `{prog} {args}` | {rc} | {join} | {f'`{saved}`' if saved else 'none'} |")
            rows += [f"|  | | ![{os.path.basename(s)}]({os.path.basename(s)}) | |" for s in shots]
        print(rows[-1], flush=True)
    with open(os.path.join(out, "steps.md"), "w") as f:
        f.write("# Installer path (docs/PLAYTEST.md, sections 2 and 3)\n\n" + "\n".join(rows) + "\n")
    print(f"Wrote {os.path.join(out, 'steps.md')}")


if __name__ == "__main__":
    main()
