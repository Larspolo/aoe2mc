import os

import mc_check

import game.run as run


def game_without_server(folder):
    g = run.Game.__new__(run.Game)            # no start(): no server process, no RCON
    g.server = g.rcon = None
    g.pack = None
    g.folder = str(folder)
    g.usercache = None
    return g


def test_stop_keeps_the_server_log(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mc_check, "workdir", lambda: str(tmp_path / "work"))
    os.makedirs(tmp_path / "work")
    folder = tmp_path / "server"
    (folder / "logs").mkdir(parents=True)
    (folder / "logs" / "latest.log").write_text("[10:00:00] [Server thread/INFO]: Done\n")
    g = game_without_server(folder)

    g.stop()

    assert not folder.exists()
    kept = tmp_path / "work" / "last-game.log"
    assert kept.read_text() == "[10:00:00] [Server thread/INFO]: Done\n"
    assert f"Server log: {kept}" in capsys.readouterr().out


def test_stop_replaces_the_old_log(tmp_path, monkeypatch):
    monkeypatch.setattr(mc_check, "workdir", lambda: str(tmp_path))
    (tmp_path / "last-game.log").write_text("old game\n")
    folder = tmp_path / "server"
    (folder / "logs").mkdir(parents=True)
    (folder / "logs" / "latest.log").write_text("new game\n")

    game_without_server(folder).stop()

    assert (tmp_path / "last-game.log").read_text() == "new game\n"


def test_stop_without_a_log_raises_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mc_check, "workdir", lambda: str(tmp_path))
    folder = tmp_path / "server"
    folder.mkdir()

    game_without_server(folder).stop()

    assert not folder.exists()
    assert not (tmp_path / "last-game.log").exists()
    assert "Server log:" not in capsys.readouterr().out
