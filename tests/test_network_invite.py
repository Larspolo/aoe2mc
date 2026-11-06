"""--host --invite: only invited Minecraft accounts join a network game (#5892)."""
import types

import pytest

from game import run


def props(**kw):
    return dict(line.split("=", 1) for line in run.properties(1, 2, "pw", **kw).splitlines() if "=" in line)


def test_local_game_is_open_and_offline():
    p = props()
    assert (p["white-list"], p["online-mode"]) == ("false", "false")
    assert "enforce-whitelist" not in p


def test_host_uses_whitelist_and_login():
    p = props(host=True)
    assert (p["white-list"], p["enforce-whitelist"], p["online-mode"]) == ("true", "true", "true")


def test_offline_keeps_whitelist():
    p = props(host=True, offline=True)
    assert (p["white-list"], p["enforce-whitelist"], p["online-mode"]) == ("true", "true", "false")


def test_whitelist_adds_each_name():
    sent = []
    game = types.SimpleNamespace(host=True, invite=("Alex", "Sam"), command=sent.append)
    run.whitelist(game)
    assert sent == ["whitelist add Alex", "whitelist add Sam"]
    sent.clear()
    run.whitelist(types.SimpleNamespace(host=False, invite=("Alex",), command=sent.append))
    assert sent == []


def test_invite_names():
    assert run.invite_names(True, "Alex, Sam", False) == ("Alex", "Sam")
    assert run.invite_names(False, None, False) == ()
    with pytest.raises(SystemExit, match="--invite"):
        run.invite_names(True, None, False)


def test_offline_warns(capsys):
    run.invite_names(True, "Alex", True)
    assert "Warning" in capsys.readouterr().out
