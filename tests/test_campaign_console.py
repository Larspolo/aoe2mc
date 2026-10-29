"""#3812: in a campaign, a line of stdin goes to the server of the current scenario, not to the stopped one."""
import os
import sys
import time

from game import run


class Server:
    def __init__(self):
        self.sent = []

    def command(self, line):
        self.sent.append(line)
        return "ok"


def test_the_next_scenario_gets_the_lines_of_the_same_thread(monkeypatch, capsys):
    r, w = os.pipe()
    monkeypatch.setattr(sys, "stdin", os.fdopen(r))
    monkeypatch.setattr(run, "CONSOLE", {})
    one, two = Server(), Server()
    t1 = run.console(one)
    os.write(w, b"say a\n")
    for _ in range(50):
        if one.sent:
            break
        time.sleep(0.05)
    t2 = run.console(two)                            # scenario 2 of the campaign starts
    os.write(w, b"say b\nsay c\n")
    os.close(w)
    t1.join(5)
    assert t2 is t1
    assert one.sent == ["say a"] and two.sent == ["say b", "say c"]
