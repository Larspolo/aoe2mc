"""A failing typed command does not end the command line of the game program (#3043)."""
import io
import sys
from types import SimpleNamespace

from game import rcon, run


def fake_game(fail=None):
    """A game with a command method that raises `fail` once. A plain namespace: the rcon_limit fixture of conftest
    wraps only the classes of a test module, and it would fail the long command with an AssertionError first."""
    game = SimpleNamespace(sent=[], fail=fail)

    def command(line):
        if game.fail:
            error, game.fail = game.fail, None
            raise error
        if len(line.encode()) > rcon.MAX:
            raise rcon.RconError(f"RCON command of {len(line.encode())} bytes, the limit is {rcon.MAX}")
        game.sent.append(line)
        return "ok"
    game.command = command
    return game


def run_console(game, monkeypatch, lines):
    monkeypatch.setattr(sys, "stdin", io.StringIO("".join(line + "\n" for line in lines)))
    run.console(game).join(5)


def test_a_command_over_the_limit_does_not_end_the_console(monkeypatch, capsys):
    game = fake_game()
    run_console(game, monkeypatch, ["say one", "say " + "x" * 1500, "say two"])
    assert game.sent == ["say one", "say two"]
    err = capsys.readouterr().err.splitlines()
    assert len(err) == 1 and str(rcon.MAX) in err[0]


def test_a_missing_connection_does_not_end_the_console(monkeypatch, capsys):
    game = fake_game(fail=AttributeError("'NoneType' object has no attribute 'command'"))
    run_console(game, monkeypatch, ["say one", "say two"])
    assert game.sent == ["say two"]
    assert "The command failed" in capsys.readouterr().err
