import faulthandler
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]
sys.path.append(os.path.join(ROOT, "game"))      # game modules import each other by name ("No module named 'bossbar'", #1045)


@pytest.fixture(autouse=True)
def empty_stdin(monkeypatch):
    """An empty stdin: the run.console thread of a test game ends at once. Else pytest prints a thread warning of about
    10 lines for each such test, and they hide the result line at the end of the output (#2510)."""
    monkeypatch.setattr(sys, "stdin", io.StringIO())


@pytest.fixture(autouse=True)
def stack_of_a_slow_test(request):
    """The stack of a fast test that runs longer than 90 s: else the suite stops at one percent with no clue (#2484).
    Not for the slow and mc tests: they can take minutes."""
    if request.node.get_closest_marker("slow") or request.node.get_closest_marker("mc"):
        yield
        return
    from _pytest.faulthandler import fault_handler_stderr_fd_key   # the real stderr: the capture hides fd 2
    faulthandler.dump_traceback_later(90, file=request.config.stash[fault_handler_stderr_fd_key])
    yield
    faulthandler.cancel_dump_traceback_later()


@pytest.fixture(autouse=True)
def no_pack_assets(monkeypatch):
    """units.ASSETS is off in each test and after it: run.Game on a world with the pack turns it on, and the
    equipment assets of the next tests made their summon commands longer (#2743)."""
    import units
    monkeypatch.setattr(units, "ASSETS", False)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """The result line also with -qq: addopts has -q, so `pytest -q` printed no "N passed" line, and runs ran the full
    suite again to find the result (#1243, #2510)."""
    if config.get_verbosity() < -1:
        counts = {k: len(v) for k, v in terminalreporter.stats.items() if k and k != "warnings"}
        terminalreporter.write_line(", ".join(f"{n} {k}" for k, n in sorted(counts.items())) + f" (exit {exitstatus})")


def entity_ids(nbt_or_desc):
    """All entity IDs of an entity and its passengers (riders)."""
    out = [str(nbt_or_desc["id"])]
    for p in nbt_or_desc.get("Passengers", []):
        out += entity_ids(p)
    return out


@pytest.fixture(scope="session")
def tiny_world(tmp_path_factory):
    """The synthetic tiny scenario, converted once per test session. Returns (world path, console output)."""
    import contextlib
    import io

    import aoe2mc
    import scenarios

    d = tmp_path_factory.mktemp("tiny")
    src = scenarios.tiny(str(d / "tiny.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(d / "TinyWorld"), preview=True)
    return str(d / "TinyWorld"), out.getvalue()


def limited(command):
    """command of a fake server that fails on a command that the RCON server refuses (rcon.MAX, #1647)."""
    from game import rcon

    def check(self, cmd, *args, **kw):
        assert len(cmd.encode()) <= rcon.MAX, f"RCON command of {len(cmd.encode())} bytes: {cmd[:80]}..."
        return command(self, cmd, *args, **kw)
    check.limited = True
    return check


@pytest.fixture(autouse=True)
def rcon_limit(request):
    """The fake servers of the tests (each class of the test module with a command method) fail on a command longer
    than rcon.MAX bytes, as the real server, which closes the connection (#1647)."""
    for obj in list(vars(request.module).values()):
        if isinstance(obj, type) and callable(vars(obj).get("command")) and not getattr(obj.command, "limited", False):
            obj.command = limited(vars(obj)["command"])
