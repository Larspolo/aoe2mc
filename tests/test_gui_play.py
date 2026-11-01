"""gui.py, tab "Play" (#1775): the argument list of game/run.py, and the start and stop of a child process. A small
script stands in for the game program: the fast tests start no server."""
import os
import queue
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

import gui

ROOT = Path(__file__).resolve().parent.parent


def test_play_argv_has_each_field():
    o = {"world": "/saves/W"}
    assert gui.play_argv(o) == ["/saves/W"]
    assert gui.play_argv(o | {"server": "vanilla"})[1:] == ["--server", "vanilla"]
    assert gui.play_argv(o | {"people": " 2 "})[1:] == ["--people", "2"]
    assert gui.play_argv(o | {"reveal": "all"})[1:] == ["--reveal", "all"]
    assert gui.play_argv(o | {"play": True})[1:] == ["--play"]
    assert gui.play_argv(o | {"bot": True})[1:] == ["--bot"]
    assert gui.play_argv(o | {"cheats": True})[1:] == ["--cheats"]
    assert gui.play_argv(o | {"server": "", "people": "", "play": False}) == gui.play_argv(o)


def test_play_argv_is_valid_for_run_py(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "game"))
    import run
    args = gui.play_argv({"world": "W", "server": "paper", "people": "1", "reveal": "normal", "play": True,
                          "bot": True, "cheats": True})
    with pytest.raises(SystemExit, match="no level.dat in W"):  # argparse accepts all options, then the world check
        run.main(args)


def fake(tmp_path, body):
    script = tmp_path / "fake.py"
    script.write_text(textwrap.dedent(body))
    return (sys.executable, "-u", str(script))


def test_stop_game_stops_like_ctrl_c(tmp_path):
    cmd = fake(tmp_path, f"""\
        import sys, time
        sys.path[:0] = [{str(ROOT / "game")!r}, {str(ROOT / "tools")!r}]
        import run
        run.ctrl_c()                               # like run.main: the parent can ignore SIGINT (a background run, #2658)
        try:                                       # the print too: SIGINT can come just after it (-n auto, #2415)
            print("ready", sys.argv[1:])
            time.sleep(60)
        except KeyboardInterrupt:
            print("Stopping the server ...")
            sys.exit(3)
        """)
    q = queue.Queue()
    p = gui.start_game(["W", "--play"], lambda s: q.put(s), lambda rc: q.put(("rc", rc)), cmd)
    assert q.get(timeout=20) == "ready ['W', '--play']\n"
    assert gui.stop_game(p, wait=20) == 3
    assert q.get(timeout=20) == "Stopping the server ...\n"
    assert q.get(timeout=20) == ("rc", 3)


def test_stop_game_kills_a_game_that_does_not_end(tmp_path):
    cmd = fake(tmp_path, """\
        import signal, subprocess, sys, time
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        print(child.pid)
        time.sleep(60)
        """)
    q = queue.Queue()
    p = gui.start_game([], q.put, lambda rc: None, cmd)
    child = int(q.get(timeout=20))
    gui.stop_game(p, wait=1)
    assert p.poll() is not None
    if sys.platform == "linux":                                 # the server (a child of run.py) stops too
        for _ in range(50):
            if not alive(child):
                break
            time.sleep(0.1)
        else:
            pytest.fail("the child of the game program still runs")


def alive(pid):
    """A zombie (killed, not yet reaped by init) is not alive."""
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def test_stdin_is_a_pipe(tmp_path):
    """run.main() reads commands with input(): with no stdin it gets EOF at once and stops the server."""
    cmd = fake(tmp_path, """\
        print("got", input())
        """)
    q = queue.Queue()
    p = gui.start_game([], q.put, lambda rc: q.put(("rc", rc)), cmd)
    p.stdin.write("help\n")
    p.stdin.flush()
    assert q.get(timeout=20) == "got help\n"
    assert q.get(timeout=20) == ("rc", 0)


def test_the_window_has_the_play_tab():
    if subprocess.run([sys.executable, "-c", "import tkinter"], capture_output=True).returncode:
        pytest.skip("no tkinter")
    code = ("import gui; w = gui.window(); w.update(); "
            "print([w.nametowidget(t).winfo_class() for t in w.winfo_children()[0].winfo_children()[0].tabs()]); "
            "w.destroy()")
    cmd = [sys.executable, "-c", code]
    if not os.environ.get("DISPLAY"):
        if not shutil.which("xvfb-run"):
            pytest.skip("no display and no xvfb-run")
        cmd = ["xvfb-run", "-a"] + cmd
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "['TFrame', 'TFrame', 'TFrame']", r.stderr
