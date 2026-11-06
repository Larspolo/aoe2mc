"""--host: the console line tells the host how to invite one more friend with no restart (#5924)."""
from game import run


def test_invite_line_names_the_whitelist_command():
    line = run.invite_line(run.invite_names(True, "Alex,Sam", False))
    assert "Type whitelist add NAME here to invite one more friend." in line


def test_console_sends_whitelist_add_to_the_server(monkeypatch):
    sent = []

    class Game:
        def command(self, line):
            sent.append(line)
            return ""

    r, w = __import__("os").pipe()
    monkeypatch.setattr(run.sys, "stdin", open(r))
    monkeypatch.setattr(run, "CONSOLE", {})
    with open(w, "w") as f:
        f.write("whitelist add eve\n")
    run.console(Game()).join(5)
    assert sent == ["whitelist add eve"]
