"""The game program on a Paper server (#434): the jar cache, the log format and a real start (marker mc)."""
import glob
import os
import shutil
import urllib.request

import pytest

from game import run


def test_joined_matches_vanilla_and_paper_logs():
    assert run.JOINED.search("[04:18:46] [Server thread/INFO]: Steve joined the game").group(1) == "Steve"
    assert run.JOINED.search("[04:18:46 INFO]: Steve joined the game").group(1) == "Steve"
    assert not run.JOINED.search("[04:18:46 INFO]: <Steve> Bob joined the game")


def test_paper_jar_takes_the_newest_cached_jar(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "PAPER", str(tmp_path))
    os.makedirs(tmp_path / "26.3")
    for i, name in enumerate(["paper-26.3-300.jar", "paper-26.3-223.jar"]):     # no network when a jar is there
        (tmp_path / "26.3" / name).write_bytes(b"")
        os.utime(tmp_path / "26.3" / name, (1000 + i, 1000 + i))
    monkeypatch.setattr(run, "get", lambda url: pytest.fail("download"))
    assert run.paper_jar("26.3").endswith("paper-26.3-223.jar")


def paper_reachable():
    if glob.glob(os.path.join(run.PAPER, "26.3", "paper-*.jar")):
        return True
    try:
        urllib.request.urlopen(urllib.request.Request(run.FILL + "/26.3/builds/latest", headers=run.AGENT),
                               timeout=10).close()
        return True
    except OSError:
        return False


@pytest.mark.mc
def test_game_starts_paper(tiny_world, tmp_path):
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        assert any("running Paper version" in line for line in game.server.log)
        assert game.command("time query gametime").startswith("The game time is")
    assert os.listdir(tmp_path) == ["W"]              # no usercache.json next to the world
    assert os.path.isfile(world / "level.dat")
