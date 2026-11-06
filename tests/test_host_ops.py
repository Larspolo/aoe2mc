"""The operators of a --host game have level 2: a friend cannot /stop the server or change the white-list (#5925)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import run  # noqa: E402


def lines(**kw):
    return run.properties(25565, 25575, "pw", **kw).splitlines()


def test_host_level_2():
    assert "op-permission-level=2" in lines(host=True)
    assert "op-permission-level=2" in lines(host=True, offline=True)


def test_local_game_unchanged():
    assert not any(x.startswith("op-permission-level") for x in lines())
