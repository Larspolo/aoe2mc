"""Stop the frozen game program as the window does (#3003): run this script with pythonw (no console, as
aoe2mc-gui.exe). It starts GAME on WORLD with gui.start_game(), waits for "Server is ready", calls gui.stop_game() and
writes the output, the times and each error to LOG. Exit 1 when the log has no "Stopping the server", the stop takes
60 s or more, or a new java.exe still runs after the stop.

    pythonw packaging/stop_check.py GAME WORLD LOG
"""
import os
import queue
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gui  # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def java():
    """The PIDs of the java.exe processes that run now."""
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq java.exe", "/FO", "CSV", "/NH"], capture_output=True,
                         text=True, creationflags=NO_WINDOW).stdout
    return {int(f[1].strip('"')) for f in (line.split(",") for line in out.splitlines()) if len(f) > 1
            and f[1].strip('"').isdigit()}


def main(game, world, log_path):
    lines, errors = queue.Queue(), []
    with open(log_path, "w") as log:
        def say(text):
            log.write(f"{time.strftime('%H:%M:%S')} {text.rstrip()}\n")
            log.flush()
        before = java()
        say(f"java.exe before the start: {sorted(before)}")
        p = gui.start_game([world], lines.put, lambda rc: lines.put(("rc", rc)), [game])
        out, end = [], time.time() + 600
        while not any("Server is ready" in s for s in out) and time.time() < end:
            try:
                s = lines.get(timeout=5)
            except queue.Empty:
                continue
            if isinstance(s, tuple):
                errors.append(f"the game program ended before the server was ready (exit code {s[1]})")
                break
            out.append(s)
            say(s)
        if not errors and not any("Server is ready" in s for s in out):
            errors.append("no \"Server is ready\" in 600 s")
        t = time.time()
        if not errors:
            try:
                say(f"gui.stop_game() returned {gui.stop_game(p)}")
            except Exception:
                errors.append(traceback.format_exc())
        took = time.time() - t
        say(f"the stop took {took:.1f} s")
        while True:                                # the last lines of the output
            try:
                s = lines.get(timeout=5)
            except queue.Empty:
                break
            if not isinstance(s, tuple):
                out.append(s)
                say(s)
        for _ in range(20):                        # the server can need a moment to end after the game program
            new = java() - before
            if not new:
                break
            time.sleep(1)
        if not any("Stopping the server" in s for s in out):
            errors.append("no \"Stopping the server\" in the output")
        if took >= 60:
            errors.append(f"the stop took {took:.0f} s")
        if new:
            errors.append(f"java.exe still runs after the stop: {sorted(new)}")
        if p.poll() is None or new:                # do not leave the game program and its server on the runner
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=NO_WINDOW)
            for pid in new:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
        for e in errors:
            say(f"ERROR: {e}")
        say("OK" if not errors else f"{len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
