"""#2740: the game program sends resourcepacks/resources.zip of the world to each player who joins."""
import hashlib
import urllib.error
import urllib.request

import pytest

from game import run

KEYS = ("resource-pack=", "resource-pack-sha1=", "require-resource-pack=true", "resource-pack-prompt=")


def world(tmp_path, data=b"PK pack bytes"):
    (tmp_path / "resourcepacks").mkdir()
    (tmp_path / "resourcepacks" / "resources.zip").write_bytes(data)
    return str(tmp_path)


def test_a_world_with_a_pack_has_the_four_keys_and_its_sha1(tmp_path):
    pack = run.PackServer(run.pack_file(world(tmp_path)))
    try:
        lines = run.properties(25565, 25575, "pw", pack).splitlines()
    finally:
        pack.stop()
    for key in KEYS:
        assert sum(line.startswith(key) for line in lines) == 1, key
    assert f"resource-pack-sha1={hashlib.sha1(b'PK pack bytes').hexdigest()}" in lines
    assert f"resource-pack={pack.url}" in lines and pack.url.startswith("http://127.0.0.1:")
    assert '{"text": "' in next(line for line in lines if line.startswith("resource-pack-prompt="))


def test_a_world_without_a_pack_has_none_of_the_keys(tmp_path):
    assert run.pack_file(str(tmp_path)) is None
    text = run.properties(25565, 25575, "pw", None)
    assert "resource-pack" not in text


def test_the_http_server_gives_the_bytes_and_stops_with_the_game(tmp_path):
    data = bytes(range(256)) * 40
    g = run.Game(world(tmp_path, data))
    g.pack = run.PackServer(run.pack_file(g.world))
    url = g.pack.url
    assert urllib.request.urlopen(url, timeout=5).read() == data
    with pytest.raises(urllib.error.HTTPError):                     # only the pack, no other file of the world
        urllib.request.urlopen(url.replace("resources.zip", "level.dat"), timeout=5)
    g.stop()
    assert g.pack is None
    with pytest.raises(OSError):
        urllib.request.urlopen(url, timeout=5)
