"""gui.py, tab "Play" (#1777): the replay fields of a recorded game, and the command line that sends commands to the
server through the stdin of the game program (run.console). Fake processes and a fake server: no Minecraft."""
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from test_gui_play import fake

import gui

ROOT = Path(__file__).resolve().parent.parent


def test_play_argv_gives_the_replay_fields():
    o = {"world": "W", "replay": True, "speed": "4", "start": "10:00", "follow": "2", "view": "1"}
    assert gui.play_argv(o) == ["W", "--speed", "4", "--from", "10:00", "--follow", "2", "--view", "1", "--replay"]
    assert gui.play_argv(o | {"follow": " ", "view": ""}) == ["W", "--speed", "4", "--from", "10:00", "--replay"]
    game = gui.play_argv(o | {"replay": False, "play": True})                # the replay fields only for a replay
    assert game == ["W", "--play"]
    assert "--play" not in gui.play_argv(o | {"play": True, "bot": True, "cheats": True})   # a replay is not a game


def test_the_replay_argv_is_valid_for_run_py(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "game"))
    import run
    args = gui.play_argv({"world": "W", "server": "paper", "replay": True, "speed": "2", "start": "1:30",
                          "follow": "1", "view": "2"})
    with pytest.raises(SystemExit, match="no level.dat in W"):  # argparse accepts all options, then the world check
        run.main(args)


def world(tmp_path, data):
    w = tmp_path / "W"
    w.mkdir(parents=True)
    if data is not None:
        (w / "aoe2mc.json").write_text(json.dumps(data))
    return str(w)


def test_only_a_world_of_a_record_has_a_timeline(tmp_path):
    assert gui.has_timeline(world(tmp_path / "a", {"objects": [], "timeline": []}))
    assert not gui.has_timeline(world(tmp_path / "b", {"objects": []}))
    assert not gui.has_timeline(world(tmp_path / "c", None))
    bad = world(tmp_path / "d", None)
    Path(bad, "aoe2mc.json").write_text("{")
    assert not gui.has_timeline(bad)
    assert not gui.has_timeline("")


def test_a_command_goes_to_the_stdin_of_the_game_program(tmp_path):
    cmd = fake(tmp_path, """\
        import sys
        for line in sys.stdin:
            print("server:", line.strip())
        """)
    q = queue.Queue()
    p = gui.start_game([], q.put, lambda rc: q.put(("rc", rc)), cmd)
    assert not gui.send_command(p, "   ")
    assert gui.send_command(p, " time set day ")
    assert q.get(timeout=20) == "server: time set day\n"
    p.stdin.close()
    assert q.get(timeout=20) == ("rc", 0)
    assert not gui.send_command(p, "help")                                   # it ended
    assert not gui.send_command(None, "help")


class Server:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return f"Set the time to 1000 ({cmd})"


def test_the_console_sends_each_line_to_the_server_while_the_game_runs(monkeypatch, capsys):
    sys.path.insert(0, str(ROOT / "game"))
    import run
    monkeypatch.setattr(sys, "stdin", io.StringIO("/time set day\n\n  list \n"))
    s = Server()
    t = run.console(s)
    assert isinstance(t, threading.Thread)
    t.join(10)
    assert not t.is_alive() and s.sent == ["time set day", "list"]
    assert capsys.readouterr().out == "Set the time to 1000 (time set day)\nSet the time to 1000 (list)\n"


def test_the_window_enables_the_replay_fields_for_a_record(tmp_path):
    if subprocess.run([sys.executable, "-c", "import tkinter"], capture_output=True).returncode:
        pytest.skip("no tkinter")
    rec, game = world(tmp_path / "r", {"timeline": []}), world(tmp_path / "g", {"objects": []})
    code = ("import gui; w = gui.window(); g = w.nametowidget(w.winfo_children()[0].winfo_children()[0].tabs()[1]); "
            "boxes = [c for c in g.winfo_children() if 'replay' in str(c.cget('text') if c.winfo_class() == "
            "'TCheckbutton' else '').lower()]; e = w.nametowidget(g.winfo_children()[1]); "
            f"e.delete(0, 'end'); e.insert(0, {game!r}); w.update(); a = boxes[0].instate(['disabled']); "
            f"e.delete(0, 'end'); e.insert(0, {rec!r}); w.update(); b = boxes[0].instate(['disabled']); "
            "print(a, b); w.destroy()")
    cmd = [sys.executable, "-c", code]
    if not os.environ.get("DISPLAY"):
        if not shutil.which("xvfb-run"):
            pytest.skip("no display and no xvfb-run")
        cmd = ["xvfb-run", "-a"] + cmd
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.split()[-2:] == ["True", "False"], r.stderr
