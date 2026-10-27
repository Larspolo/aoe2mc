"""The watcher of an owner demo (game/demo_watch.py, the `demo` skill) on a fake server folder."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import demo_watch  # noqa: E402

TRACEBACK = ["Traceback (most recent call last):", '  File "game/run.py", line 418, in main',
             "rcon.RconError: the server closed the RCON connection"]


def setup(tmp_path):
    folder, out, shots = tmp_path / "tmpserver", tmp_path / "demo", tmp_path / "shots"
    for d in (folder / "logs", out, shots):
        d.mkdir(parents=True)
    (shots / "old.png").write_bytes(b"")
    (folder / "logs" / "latest.log").write_text("[17:16:03] [Server thread/INFO]: Done (36.071s)!\n")
    return folder, out, shots, tmp_path / "game.log"


def add(path, *lines, end="\n"):
    with open(path, "a") as f:
        f.write("\n".join(lines) + end)


def test_the_watch_gives_chat_errors_crashes_and_new_screenshots_once(tmp_path):
    folder, out, shots, game = setup(tmp_path)
    w = demo_watch.Watch(str(folder), str(out), str(game), str(shots))
    assert w.poll() == []
    log = folder / "logs" / "latest.log"
    add(log, "[17:22:56] [Async Chat Thread - #0/INFO]: [Not Secure] <Larspolo> Show a square on the map",
        "[17:23:01] [Server thread/ERROR]: Could not pass event PlayerInteractEvent to aoe2mc v1",
        "[17:23:02] [Server thread/INFO]: Larspolo has made the advancement [Getting Wood]")
    add(game, "Join the server localhost:49169 (Minecraft 26.3).", *TRACEBACK)
    (shots / "2026-10-27_17.23.05.png").write_bytes(b"")
    assert w.poll() == [("CHAT", "<Larspolo> Show a square on the map"),
                        ("ERROR", "[17:23:01] [Server thread/ERROR]: Could not pass event PlayerInteractEvent to aoe2mc v1"),
                        ("CRASH", TRACEBACK[-1]), ("SHOT", str(shots / "2026-10-27_17.23.05.png"))]
    assert w.poll() == []
    assert "Show a square on the map" in (out / "server.log").read_text()


def test_a_new_watch_of_the_same_game_gives_only_new_events(tmp_path):
    folder, out, shots, game = setup(tmp_path)
    log = folder / "logs" / "latest.log"
    demo_watch.Watch(str(folder), str(out), str(game), str(shots)).poll()
    add(log, "[17:30:00] [Async Chat Thread - #0/INFO]: <Larspolo> The bot is too slow")
    add(game, TRACEBACK[0])                                       # the rest of the traceback comes later
    assert demo_watch.Watch(str(folder), str(out), str(game), str(shots)).poll() == [
        ("CHAT", "<Larspolo> The bot is too slow")]
    add(game, *TRACEBACK[1:])
    assert demo_watch.Watch(str(folder), str(out), str(game), str(shots)).poll() == [("CRASH", TRACEBACK[-1])]


def test_a_line_without_its_newline_waits_for_the_next_poll(tmp_path):
    folder, out, shots, game = setup(tmp_path)
    w = demo_watch.Watch(str(folder), str(out), str(game), str(shots))
    log = folder / "logs" / "latest.log"
    add(log, "[17:31:00] [Async Chat Thread - #0/INFO]: <Larspolo> half", end="")
    assert w.poll() == []
    add(log, " a line")
    assert w.poll() == [("CHAT", "<Larspolo> half a line")]


def test_the_stop_comes_once_and_the_copied_log_stays(tmp_path):
    folder, out, shots, game = setup(tmp_path)
    w = demo_watch.Watch(str(folder), str(out), str(game), str(shots))
    add(folder / "logs" / "latest.log", "[17:23:20] [Server thread/INFO]: Stopping server")
    assert w.poll() == [("STOP", "")]
    (folder / "logs" / "latest.log").unlink()
    (folder / "logs").rmdir()
    folder.rmdir()                                                # Game.stop deletes the server folder
    assert w.poll() == []
    assert "Stopping server" in (out / "server.log").read_text()


def test_the_run_stops_quiet_seconds_after_the_last_event(tmp_path):
    folder, out, shots, game = setup(tmp_path)
    w = demo_watch.Watch(str(folder), str(out), str(game), str(shots))
    now, printed = [0.0], []

    def sleep(s):
        now[0] += s
        if now[0] == 3:
            add(folder / "logs" / "latest.log", "[17:40:00] [Async Chat Thread - #0/INFO]: <Larspolo> one")
    assert w.run(quiet=5, clock=lambda: now[0], sleep=sleep, out=lambda s, **k: printed.append(s)) == 0
    assert printed == ["CHAT <Larspolo> one"] and now[0] == 8


def test_the_run_gives_up_after_hours_without_an_event(tmp_path):
    folder, out, shots, game = setup(tmp_path)
    now, printed = [0.0], []

    def sleep(s):
        now[0] += 600
    w = demo_watch.Watch(str(folder), str(out), str(game), str(shots))
    assert w.run(hours=1, clock=lambda: now[0], sleep=sleep, out=lambda s, **k: printed.append(s)) == 1
    assert printed == ["No event in 1 hours."]
