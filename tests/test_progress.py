"""The progress line of the long conversion phases (#691)."""
import io

import aoe2mc


class Tty(io.StringIO):
    def isatty(self):
        return True


def test_progress_line_on_a_terminal_each_2_s():
    now = [100.0]
    out = Tty()
    p = aoe2mc.Progress("chunks", 200, out=out, clock=lambda: now[0])
    for done, t in ((0, 100.0), (10, 101.9), (44, 102.0), (60, 103.0), (150, 104.5)):
        now[0] = t
        p.step(done)
    p.close()
    lines = out.getvalue().split("\r")
    assert lines[1:3] == ["  chunks 44/200 (22 %), 2 s", "  chunks 150/200 (75 %), 4 s"]
    assert lines[-2:] == [" " * len("\r  chunks 150/200 (75 %), 4 s"), ""]   # close() clears the line


def test_no_progress_without_a_terminal():
    now = [0.0]
    out = io.StringIO()
    p = aoe2mc.Progress("chunks", 10, out=out, clock=lambda: now[0])
    for i in range(10):
        now[0] += 5
        p.step(i)
    p.close()
    assert out.getvalue() == ""


def test_convert_output_without_a_terminal(tiny_world):
    _, log = tiny_world
    assert "\r" not in log
