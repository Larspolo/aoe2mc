"""A window for the converter (#1540): select a scenario or a recorded game, set the main options and click "Convert".
The world goes into the Minecraft saves folder. The tab "Play" starts the game program (game/run.py) on a world as a
child process and stops it (#1775), replays a recorded game and sends the commands of its command line to the server
(#1777). The logic is in pure functions (argv, saves_folder, world_name, convert, play_argv, has_timeline, start_game,
send_command, stop_game) that the tests call without a display: tkinter loads only in window(), and many Python installs (also the
cloud environment) have no tkinter."""
import contextlib
import glob
import io
import json
import os
import platform
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import traceback
from pathlib import Path

INPUTS = (".aoe2scenario", ".aoe2record", ".mgz", ".mgx", ".mgl", ".scx")
RECORDS = (".aoe2record", ".mgz", ".mgx", ".mgl")                  # --at works only for these (aoe2mc.RECORDS)
RANDOM_MAPS = ("arabia", "arena", "black_forest", "gold_rush", "highland", "islands", "mediterranean", "nomad")  # (#1871)
VALUES = (("name", "--name"), ("tile_size", "--tile-size"), ("level_height", "--level-height"),
          ("architecture", "--architecture"), ("seed", "--seed"))
FLAGS = (("preview", "--preview"), ("no_units", "--no-units"), ("resource_pack", "--resource-pack"))
PACK_TEXT = "AoE2 look (resource pack, 4.8 MB, about +1 % frame time)"   # docs/resourcepack.md, "Cost" (#2747)
GAME = Path(__file__).resolve().parent / "game" / "run.py"
PLAY_VALUES = (("server", "--server"), ("people", "--people"), ("reveal", "--reveal"))
PLAY_FLAGS = (("play", "--play"), ("bot", "--bot"), ("cheats", "--cheats"))
BOT_VALUES = (("bot_attack", "--bot-attack"),)                     # only with --bot (#1870)
JAVA = {"26.3": 25}                                    # Java of each Minecraft version (mc_check reads the version JSON)
JDK_INSTALL = {"Linux": "sudo apt-get install openjdk-{n}-jdk-headless", "Darwin": "brew install openjdk@{n}",
               "Windows": "Install the JDK {n} from https://adoptium.net/temurin/releases/?version={n}"}
REPLAY_VALUES = (("speed", "--speed"), ("start", "--from"), ("follow", "--follow"), ("view", "--view"))


def argv(o):
    """The argument list of aoe2mc.main() from the dict o of the window fields. An empty field keeps the default of
    the converter; "More options" is split as a shell line. A random map (--random-map) takes no input file."""
    kind = o.get("random_map")
    a = [str(o["output"]), "--random-map", kind] if kind else [str(o["input"]), str(o["output"])]
    for key, flag in VALUES:
        v = str(o.get(key) or "").strip()
        if v:
            a += [flag, v]
    a += [flag for key, flag in FLAGS if o.get(key)]
    at = str(o.get("at") or "").strip()
    if at and not kind and str(o["input"]).lower().endswith(RECORDS):
        a += ["--at", at]
    return a + shlex.split(o.get("more") or "")


def saves_folder(system=None, env=None):
    """The Minecraft Java saves folder of the operating system (platform.system()) with the environment env."""
    system = system or platform.system()
    env = os.environ if env is None else env
    home = Path(env.get("HOME") or env.get("USERPROFILE") or Path.home())
    if system == "Windows":
        return Path(env.get("APPDATA") or home / "AppData" / "Roaming") / ".minecraft" / "saves"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "minecraft" / "saves"
    return home / ".minecraft" / "saves"


def world_name(path, folder=None):
    """The default world folder name for the input file path: its name without the extension, with " 2", " 3" ...
    when the saves folder has that name already."""
    folder = Path(folder or saves_folder())
    stem, n = Path(path).stem, 1
    name = stem
    while (folder / name).exists():
        n += 1
        name = f"{stem} {n}"
    return name


class Stream(io.TextIOBase):
    """A text stream that sends each write to a function (the window reads the output of the converter)."""
    def __init__(self, send):
        self.send = send

    def write(self, s):
        self.send(s)
        return len(s)


def convert(args, write):
    """Run aoe2mc.main(args) and send its output to write. Returns None, or the error text for a dialog."""
    import aoe2mc
    out = Stream(write)
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            aoe2mc.main(args)
        except SystemExit as e:                                     # argparse: a wrong option (the text is in out)
            return None if e.code in (0, None) else "The converter stopped: see the output."
        except Exception as e:
            traceback.print_exc()
            return f"{type(e).__name__}: {e}"


def javas():
    """The java binaries that mc_check.find_java looks at, in its order (apt installs into /usr/lib/jvm)."""
    cache = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "aoe2mc", "mc")
    return [j for j in [shutil.which("java")] + sorted(glob.glob("/usr/lib/jvm/*/bin/java"))
            + sorted(glob.glob(os.path.join(cache, "jdk-*", "*", "bin", "java"))) if j]


def java_problem(version="26.3", jdk=True, system=None, found=None, run=subprocess.run, exists=os.path.exists):
    """None when game/run.py finds the Java of the Minecraft version (and javac for the Paper plugin, jdk), else the
    text for the user with the install step of the system (#1776)."""
    need = JAVA.get(version, 25)
    step = JDK_INSTALL.get(system or platform.system(), JDK_INSTALL["Windows"]).format(n=need)
    best = 0
    for java in javas() if found is None else found:
        try:
            out = run([java, "-XshowSettings:properties", "-version"], capture_output=True, text=True).stderr
        except OSError:
            continue
        major = int(m.group(1)) if (m := re.search(r'version "(\d+)', out)) else 0
        best = max(best, major)
        if major < need:
            continue
        home = m.group(1).strip() if (m := re.search(r"^\s*java\.home = (.+)$", out, re.M)) else \
            os.path.dirname(os.path.dirname(os.path.realpath(java)))
        if not jdk or any(exists(os.path.join(home, "bin", n)) for n in ("javac", "javac.exe")):
            return None
        return (f"Java {major} has no javac (it is a JRE): the Paper plugin needs the JDK {need}.\n{step}\n"
                "Or select the server \"vanilla\".")
    have = f"Java {best} is too old" if best else "No Java was found"
    return f"{have}: Minecraft {version} needs Java {need}.\n{step}"


def play_argv(o):
    """The argument list of game/run.py from the dict o of the fields of the tab "Play". An empty field keeps the
    default of the game program."""
    a = [str(o["world"])]
    replay = bool(o.get("replay"))                                 # a replay is not a game: no --play, --bot, --cheats
    bot = bool(o.get("bot")) and not replay
    for key, flag in PLAY_VALUES + REPLAY_VALUES * replay + BOT_VALUES * bot:
        v = str(o.get(key) or "").strip()
        if v:
            a += [flag, v]
    return a + ["--replay"] * replay + [flag for key, flag in PLAY_FLAGS * (not replay) if o.get(key)]


def has_timeline(world):
    """True when the world was converted from a recorded game: its aoe2mc.json has a "timeline" (run.py --replay)."""
    try:
        with open(os.path.join(world, "aoe2mc.json")) as f:
            return "timeline" in json.load(f)
    except (OSError, ValueError):
        return False


def game_command():
    """The command of the game program: game/run.py with this Python, or in an app bundle (sys.frozen) the program
    aoe2mc-game next to the window (#1778)."""
    if getattr(sys, "frozen", False):
        return (str(Path(sys.executable).with_name("aoe2mc-game" + (".exe" if os.name == "nt" else ""))),)
    return sys.executable, "-u", str(GAME)


def start_game(args, write, done, cmd=None):
    """Start the game program with args as a child process. A thread sends each line of its output to write, and its
    exit code to done at the end. stdin is a pipe: with no stdin, input() in run.main() ends the game at once."""
    p = subprocess.Popen([*(cmd or game_command()), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, start_new_session=os.name != "nt",
                         creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

    def read():
        for line in p.stdout:
            write(line)
        done(p.wait())
    threading.Thread(target=read, daemon=True).start()
    return p


def send_command(p, text):
    """Send the command text to the stdin of the game program p (run.console sends it to the server). Returns False
    when the line is empty or the game program does not run."""
    text = text.strip()
    if not text or p is None or p.poll() is not None:
        return False
    try:
        p.stdin.write(text + "\n")
        p.stdin.flush()
    except OSError:                                                # it ended just now
        return False
    return True


def stop_game(p, wait=30):
    """Stop the game program like Ctrl-C: run.main() then stops the server in all modes (--play does not read stdin).
    Kill its process group (with the server) when it does not end in wait seconds. Returns the exit code."""
    if p.poll() is not None:
        return p.returncode
    p.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
    try:
        return p.wait(wait)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            p.kill()
        else:
            os.killpg(p.pid, signal.SIGKILL)
        return p.wait()


def window():
    """The converter window (not yet in its main loop)."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    import buildings
    root = tk.Tk()
    root.title("aoe2mc: AoE2 to Minecraft")
    top = ttk.Frame(root, padding=8)
    top.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    top.columnconfigure(0, weight=1)
    tabs = ttk.Notebook(top)
    tabs.grid(row=0, column=0, sticky="ew")
    f, g = ttk.Frame(tabs, padding=4), ttk.Frame(tabs, padding=4)
    tabs.add(f, text="Convert")
    tabs.add(g, text="Play")
    f.columnconfigure(1, weight=1)
    g.columnconfigure(1, weight=1)
    v = {k: tk.StringVar() for k in ("input", "output", "name", "tile_size", "level_height", "architecture", "seed",
                                     "random_map", "at", "more", "world", "server", "people", "reveal", "speed", "start",
                                     "follow", "view", "command", "bot_attack")}
    v |= {k: tk.BooleanVar() for k, _ in FLAGS + PLAY_FLAGS + (("replay", ""),)}
    v["server"].set("paper")
    v["people"].set("1")
    v["reveal"].set("normal")
    v["play"].set(True)
    v["speed"].set("1")
    v["start"].set("0:00")
    v["bot_attack"].set("10:00")
    v["tile_size"].set("4")
    v["level_height"].set("3")
    v["seed"].set("1")
    v["preview"].set(True)

    def pick_input():
        p = filedialog.askopenfilename(filetypes=[("AoE2 scenario or recorded game", " ".join("*" + e for e in INPUTS)),
                                                  ("All files", "*")])
        if p:
            v["input"].set(p)
            v["output"].set(str(saves_folder() / world_name(p)))

    def pick_output():
        p = filedialog.askdirectory(initialdir=str(saves_folder()) if saves_folder().is_dir() else None)
        if p:
            v["output"].set(p)

    rows = (("Input file", "input", pick_input), ("Random map (no input file)", "random_map", None),
            ("World folder", "output", pick_output), ("World name", "name", None),
            ("Tile size (blocks)", "tile_size", None), ("Level height (blocks)", "level_height", None),
            ("Architecture", "architecture", None), ("Seed", "seed", None), ("Time (MM:SS, record)", "at", None),
            ("More options", "more", None))
    for r, (label, key, browse) in enumerate(rows):
        ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=2)
        if key == "architecture":
            e = ttk.Combobox(f, textvariable=v[key], values=[""] + sorted(buildings.ARCH), state="readonly")
        elif key == "random_map":
            e = ttk.Combobox(f, textvariable=v[key], values=("",) + RANDOM_MAPS, state="readonly")
        else:
            e = ttk.Entry(f, textvariable=v[key], width=50)
        e.grid(row=r, column=1, sticky="ew", padx=4)
        if browse:
            ttk.Button(f, text="Browse...", command=browse).grid(row=r, column=2)
    checks = ttk.Frame(f)
    checks.grid(row=len(rows), column=1, sticky="w")
    ttk.Checkbutton(checks, text="Preview image", variable=v["preview"]).pack(side="left")
    ttk.Checkbutton(checks, text="No units", variable=v["no_units"]).pack(side="left", padx=8)
    ttk.Checkbutton(checks, text=PACK_TEXT, variable=v["resource_pack"]).pack(side="left")
    go = ttk.Button(f, text="Convert")
    go.grid(row=len(rows) + 1, column=1, pady=6)

    def pick_world():
        p = filedialog.askdirectory(initialdir=str(saves_folder()) if saves_folder().is_dir() else None)
        if p:
            v["world"].set(p)

    ttk.Label(g, text="World folder").grid(row=0, column=0, sticky="w", pady=2)
    ttk.Entry(g, textvariable=v["world"], width=50).grid(row=0, column=1, sticky="ew", padx=4)
    ttk.Button(g, text="Browse...", command=pick_world).grid(row=0, column=2)
    for r, (label, key, values) in enumerate((("Server", "server", ("paper", "vanilla")),
                                              ("Reveal map", "reveal", ("normal", "all"))), 1):
        ttk.Label(g, text=label).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Combobox(g, textvariable=v[key], values=values, state="readonly").grid(row=r, column=1, sticky="w", padx=4)
    ttk.Label(g, text="People (players 1 to N)").grid(row=3, column=0, sticky="w", pady=2)
    ttk.Spinbox(g, textvariable=v["people"], from_=1, to=8, width=5).grid(row=3, column=1, sticky="w", padx=4)
    checks = ttk.Frame(g)
    checks.grid(row=4, column=1, sticky="w")
    for key, text in (("play", "Play (villagers gather)"), ("bot", "Bot plays player 2"), ("cheats", "Cheat codes")):
        ttk.Checkbutton(checks, text=text, variable=v[key]).pack(side="left", padx=(0, 8))
    ttk.Label(checks, text="Bot attacks at (MM:SS)").pack(side="left")
    bot_attack = ttk.Entry(checks, textvariable=v["bot_attack"], width=7)
    bot_attack.pack(side="left", padx=(2, 0))
    v["bot"].trace_add("write", lambda *_: bot_attack.state(["!disabled" if v["bot"].get() else "disabled"]))
    bot_attack.state(["disabled"])
    replay = ttk.Checkbutton(g, text="Replay the recorded game (instead of a game)", variable=v["replay"])
    replay.grid(row=5, column=1, sticky="w")
    fields = ttk.Frame(g)
    fields.grid(row=6, column=1, sticky="w")
    replay_widgets = [replay]
    for label, key, width in (("Speed", "speed", 5), ("From (MM:SS)", "start", 7), ("Follow player", "follow", 3),
                              ("View of player", "view", 3)):
        ttk.Label(fields, text=label).pack(side="left")
        replay_widgets.append(ttk.Entry(fields, textvariable=v[key], width=width))
        replay_widgets[-1].pack(side="left", padx=(2, 8))

    def check_world(*_):                                            # the replay fields need a recorded game
        ok = has_timeline(v["world"].get())
        for w in replay_widgets:
            w.state(["!disabled" if ok else "disabled"])
        if not ok:
            v["replay"].set(False)
    v["world"].trace_add("write", check_world)
    check_world()
    buttons = ttk.Frame(g)
    buttons.grid(row=7, column=1, pady=6)
    play = ttk.Button(buttons, text="Start game")
    play.pack(side="left")
    halt = ttk.Button(buttons, text="Stop", state="disabled")
    halt.pack(side="left", padx=8)
    log = scrolledtext.ScrolledText(top, height=14, width=80, state="disabled")
    log.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
    top.rowconfigure(1, weight=1)
    line = ttk.Frame(top)
    line.grid(row=2, column=0, sticky="ew", pady=(4, 0))
    line.columnconfigure(1, weight=1)
    ttk.Label(line, text="Command").grid(row=0, column=0, sticky="w")
    command = ttk.Entry(line, textvariable=v["command"])
    command.grid(row=0, column=1, sticky="ew", padx=4)
    q = queue.Queue()                                              # worker → window: Tk is not thread safe
    game = []                                                      # the running game program, or empty

    def start():
        o = {k: x.get() for k, x in v.items()}
        if not (o["input"] or o["random_map"]) or not o["output"]:
            messagebox.showerror("aoe2mc", "Select the input file (or a random map) and the world folder.")
            return
        try:
            args = argv(o)
        except ValueError as e:                                     # shlex: an open quote in "More options"
            messagebox.showerror("aoe2mc", f"More options: {e}")
            return
        go.state(["disabled"])
        threading.Thread(target=lambda: q.put(("done", convert(args, lambda s: q.put(("text", s))), o["output"])),
                         daemon=True).start()

    def start_play():
        o = {k: x.get() for k, x in v.items()}
        if not o["world"] or not os.path.isfile(os.path.join(o["world"], "level.dat")):
            messagebox.showerror("aoe2mc", "Select a world folder (a folder with level.dat).")
            return
        if o["bot"] and str(o["people"]).strip() not in ("", "1"):
            messagebox.showerror("aoe2mc", "The bot plays player 2: use it with one person only.")
            return
        if problem := java_problem(jdk=o["server"] != "vanilla"):
            messagebox.showerror("aoe2mc", problem)
            return
        play.state(["disabled"])
        halt.state(["!disabled"])
        try:
            game[:] = [start_game(play_argv(o), lambda s: q.put(("text", s)), lambda rc: q.put(("ended", rc)))]
        except OSError as e:
            play.state(["!disabled"])
            halt.state(["disabled"])
            messagebox.showerror("aoe2mc", f"The game program did not start: {e}")

    def send(*_):
        text = v["command"].get()
        if send_command(game[0] if game else None, text):
            q.put(("text", f"> {text.strip()}\n"))
            v["command"].set("")
        elif text.strip():
            q.put(("text", "No game runs: start a game first.\n"))

    def stop_play(then=None):
        halt.state(["disabled"])
        if game:
            threading.Thread(target=lambda: (stop_game(game[0]), then and q.put((then,))), daemon=True).start()
        elif then:
            q.put((then,))

    def poll():
        while not q.empty():
            item = q.get()
            if item[0] == "text":
                log.configure(state="normal")
                log.insert("end", item[1])
                log.see("end")
                log.configure(state="disabled")
            elif item[0] == "ended":
                game.clear()
                play.state(["!disabled"])
                halt.state(["disabled"])
                q.put(("text", f"The game program ended (exit code {item[1]}).\n"))
            elif item[0] == "quit":
                root.destroy()
                return
            else:
                go.state(["!disabled"])
                if item[1]:
                    messagebox.showerror("aoe2mc", item[1])
                else:
                    v["world"].set(item[2])
                    messagebox.showinfo("aoe2mc", f"The world is in {item[2]}.\nOpen it in Minecraft Java 26.3, "
                                        "or start a game on it in the tab \"Play\".")
        root.after(100, poll)

    go.configure(command=start)
    play.configure(command=start_play)
    halt.configure(command=stop_play)
    command.bind("<Return>", send)
    root.protocol("WM_DELETE_WINDOW", lambda: stop_play("quit"))   # the server must not stay up after the window
    root.after(100, poll)
    return root


def run():
    """The entry point of aoe2mc-gui."""
    window().mainloop()


if __name__ == "__main__":
    run()
