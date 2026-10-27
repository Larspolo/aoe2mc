"""A window for the converter (#1540): select a scenario or a recorded game, set the main options and click "Convert".
The world goes into the Minecraft saves folder. The logic is in pure functions (argv, saves_folder, world_name,
convert) that the tests call without a display: tkinter loads only in window(), and many Python installs (also the
cloud environment) have no tkinter."""
import contextlib
import io
import os
import platform
import queue
import shlex
import threading
import traceback
from pathlib import Path

INPUTS = (".aoe2scenario", ".aoe2record", ".mgz", ".mgx", ".mgl", ".scx")
RECORDS = (".aoe2record", ".mgz", ".mgx", ".mgl")                  # --at works only for these (aoe2mc.RECORDS)
VALUES = (("name", "--name"), ("tile_size", "--tile-size"), ("level_height", "--level-height"),
          ("architecture", "--architecture"), ("seed", "--seed"))
FLAGS = (("preview", "--preview"), ("no_units", "--no-units"))


def argv(o):
    """The argument list of aoe2mc.main() from the dict o of the window fields. An empty field keeps the default of
    the converter; "More options" is split as a shell line."""
    a = [str(o["input"]), str(o["output"])]
    for key, flag in VALUES:
        v = str(o.get(key) or "").strip()
        if v:
            a += [flag, v]
    a += [flag for key, flag in FLAGS if o.get(key)]
    at = str(o.get("at") or "").strip()
    if at and str(o["input"]).lower().endswith(RECORDS):
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


def window():
    """The converter window (not yet in its main loop)."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    import buildings
    root = tk.Tk()
    root.title("aoe2mc: AoE2 to Minecraft")
    f = ttk.Frame(root, padding=8)
    f.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    f.columnconfigure(1, weight=1)
    v = {k: tk.StringVar() for k in ("input", "output", "name", "tile_size", "level_height", "architecture", "seed",
                                     "at", "more")}
    v |= {k: tk.BooleanVar() for k, _ in FLAGS}
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

    rows = (("Input file", "input", pick_input), ("World folder", "output", pick_output), ("World name", "name", None),
            ("Tile size (blocks)", "tile_size", None), ("Level height (blocks)", "level_height", None),
            ("Architecture", "architecture", None), ("Seed", "seed", None), ("Time (MM:SS, record)", "at", None),
            ("More options", "more", None))
    for r, (label, key, browse) in enumerate(rows):
        ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=2)
        if key == "architecture":
            e = ttk.Combobox(f, textvariable=v[key], values=[""] + sorted(buildings.ARCH), state="readonly")
        else:
            e = ttk.Entry(f, textvariable=v[key], width=50)
        e.grid(row=r, column=1, sticky="ew", padx=4)
        if browse:
            ttk.Button(f, text="Browse...", command=browse).grid(row=r, column=2)
    checks = ttk.Frame(f)
    checks.grid(row=len(rows), column=1, sticky="w")
    ttk.Checkbutton(checks, text="Preview image", variable=v["preview"]).pack(side="left")
    ttk.Checkbutton(checks, text="No units", variable=v["no_units"]).pack(side="left", padx=8)
    go = ttk.Button(f, text="Convert")
    go.grid(row=len(rows) + 1, column=1, pady=6)
    log = scrolledtext.ScrolledText(f, height=14, width=80, state="disabled")
    log.grid(row=len(rows) + 2, column=0, columnspan=3, sticky="nsew")
    f.rowconfigure(len(rows) + 2, weight=1)
    q = queue.Queue()                                              # worker → window: Tk is not thread safe

    def start():
        o = {k: x.get() for k, x in v.items()}
        if not o["input"] or not o["output"]:
            messagebox.showerror("aoe2mc", "Select the input file and the world folder.")
            return
        try:
            args = argv(o)
        except ValueError as e:                                     # shlex: an open quote in "More options"
            messagebox.showerror("aoe2mc", f"More options: {e}")
            return
        go.state(["disabled"])
        threading.Thread(target=lambda: q.put(("done", convert(args, lambda s: q.put(("text", s))), o["output"])),
                         daemon=True).start()

    def poll():
        while not q.empty():
            item = q.get()
            if item[0] == "text":
                log.configure(state="normal")
                log.insert("end", item[1])
                log.see("end")
                log.configure(state="disabled")
            else:
                go.state(["!disabled"])
                if item[1]:
                    messagebox.showerror("aoe2mc", item[1])
                else:
                    messagebox.showinfo("aoe2mc", f"The world is in {item[2]}.\nOpen it in Minecraft Java 26.3.")
        root.after(100, poll)

    go.configure(command=start)
    root.after(100, poll)
    return root


def run():
    """The entry point of aoe2mc-gui."""
    window().mainloop()


if __name__ == "__main__":
    run()
