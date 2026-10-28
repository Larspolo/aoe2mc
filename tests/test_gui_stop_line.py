"""gui.stop_game() on Windows (#3003): the window has no console, so it cannot send Ctrl-Break to the game program.
It writes the stop line to its stdin, and run.console interrupts the main thread. A Linux test takes the same path."""
import queue
from pathlib import Path

import gui
from test_gui_play import fake

ROOT = Path(__file__).resolve().parent.parent


def test_the_stop_line_stops_a_game_that_does_not_read_stdin(tmp_path):
    cmd = fake(tmp_path, f"""\
        import sys, time
        sys.path[:0] = [{str(ROOT / "game")!r}, {str(ROOT / "tools")!r}]
        import run
        run.ctrl_c()

        class Game:
            def command(self, line):
                return "answer " + line

        try:
            run.console(Game())                    # the main thread does not read stdin, as with --play
            print("ready")
            time.sleep(60)
        except KeyboardInterrupt:
            print("Stopping the server ...")
            sys.exit(3)
        """)
    q = queue.Queue()
    p = gui.start_game(["W", "--play"], q.put, lambda rc: q.put(("rc", rc)), cmd)
    assert q.get(timeout=20) == "ready\n"
    assert gui.send_command(p, "list")
    assert q.get(timeout=20) == "answer list\n"   # the console thread still sends the other lines to the server
    assert gui.stop_game(p, wait=20, line=True) == 3
    assert q.get(timeout=20) == "Stopping the server ...\n"
    assert q.get(timeout=20) == ("rc", 3)


def test_the_window_and_the_game_program_know_the_same_stop_line(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "game"))
    import run
    assert gui.STOP_LINE == run.STOP_LINE
    assert gui.STOP_LINE.strip() == gui.STOP_LINE and "/" not in gui.STOP_LINE   # run.console strips the lines

