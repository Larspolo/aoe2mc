"""--host with --invite: the console names the invited players, not "each person can join" (#5913)."""
from game import run


def test_invite_line_names_the_invited_players():
    names = run.invite_names(True, "Alex,Sam", False)
    line = run.invite_line(names)
    assert line == "Only these Minecraft names can join: Alex, Sam."


def test_invite_line_has_no_open_server_warning():
    line = run.invite_line(run.invite_names(True, "Alex,Sam", False))
    assert "each person on the network can join" not in line
