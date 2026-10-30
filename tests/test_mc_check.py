"""tools/mc_check.py: problem lines in a server log, and a real server run on the tiny world (marker mc)."""
import urllib.error
import urllib.request

import mc_check
import pytest

LOG = """[17:14:40] [Server thread/INFO]: Starting minecraft server version 26.3
[17:14:40] [Yggdrasil Key Fetcher/ERROR]: Failed to request yggdrasil public key
com.mojang.authlib.exceptions.MinecraftClientException: Failed to read from https://api.minecraftservices.com/publickeys
Caused by: java.net.UnknownHostException: api.minecraftservices.com
[17:14:42] [Server thread/WARN]: **** SERVER IS RUNNING IN OFFLINE/INSECURE MODE!
[17:17:13] [Server thread/ERROR]: Recoverable errors when loading section [2, 3, 2]: (Unknown registry key)
[17:17:14] [Server thread/INFO]: Done (1.533s)! For help, type "help\"""".split("\n")


def test_problems_ignore_harmless_entries_with_their_stack_trace():
    assert mc_check.problems(LOG) == [LOG[5]]


def test_java_for_tries_apt_then_download_then_explains(monkeypatch):
    calls = []
    monkeypatch.setattr(mc_check, "version_json", lambda v: {"javaVersion": {"majorVersion": 25}})
    monkeypatch.setattr(mc_check, "find_java", lambda need: calls.append("find") and None)
    monkeypatch.setattr(mc_check.os, "geteuid", lambda: 0)
    monkeypatch.setattr(mc_check.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(mc_check.subprocess, "run", lambda cmd, **kw: calls.append(cmd[1]) or
                        type("R", (), {"returncode": 0})())

    def forbidden(url):
        calls.append("download")
        raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
    monkeypatch.setattr(mc_check, "get", forbidden)
    with pytest.raises(SystemExit, match="apt-get install -y openjdk-25-jre-headless"):
        mc_check.java_for("26.3")
    assert calls == ["find", "update", "install", "find", "download"]


def mojang_reachable():
    try:
        urllib.request.urlopen(mc_check.MANIFEST, timeout=10).close()
        return True
    except OSError:
        return False


@pytest.mark.mc
def test_server_loads_tiny_world(tiny_world):
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    bad, log = mc_check.check(tiny_world[0])
    assert any("Done (" in line for line in log)
    assert any("Saved the game" in line for line in log)
    assert bad == []


@pytest.mark.mc
def test_server_loads_border_of_tiny_world(tmp_path):
    import contextlib
    import io

    import scenarios

    import aoe2mc
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    bad, log = mc_check.check(str(tmp_path / "W"), "26.3")
    assert any("Saved the game" in line for line in log)
    assert any("world border is currently 96" in line for line in log)      # the map edge, #172
    assert bad == []


@pytest.mark.mc
def test_server_loads_custom_biomes(tmp_path):
    """--ambience full (#219): the biome files and the custom biome names in the chunks load without errors."""
    import contextlib
    import io

    import scenarios

    import aoe2mc
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"), ambience="full")
    bad, log = mc_check.check(str(tmp_path / "W"), "26.3")
    assert any("Saved the game" in line for line in log)
    assert bad == []
