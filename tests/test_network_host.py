"""--host opens the game to the network (#5891)."""
import socket
import urllib.request

from game import run


def server_ip(text):
    return [line for line in text.splitlines() if line.startswith("server-ip=")]


def test_properties_host():
    assert server_ip(run.properties(1, 2, "pw")) == ["server-ip=127.0.0.1"]
    assert server_ip(run.properties(1, 2, "pw", host=True)) == ["server-ip="]


class FakeSocket:
    def __init__(self, *a, fail=False):
        self.fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def connect(self, address):
        if self.fail:
            raise OSError("no network")

    def getsockname(self):
        return ("192.168.1.20", 5000)


def test_network_address(monkeypatch):
    monkeypatch.setattr(socket, "socket", FakeSocket)
    assert run.network_address() == "192.168.1.20"
    monkeypatch.setattr(socket, "socket", lambda *a: FakeSocket(fail=True))
    assert run.network_address() == "127.0.0.1"


def test_pack_server_host(tmp_path, monkeypatch):
    path = tmp_path / "resources.zip"
    path.write_bytes(b"pack")
    real = run.network_address()
    pack = run.PackServer(str(path), host=True)
    try:
        assert pack.url.startswith(f"http://{real}:") and pack.http.server_address[0] == "0.0.0.0"
        assert urllib.request.urlopen(pack.url, timeout=5).read() == b"pack"
    finally:
        pack.stop()
    local = run.PackServer(str(path))
    try:
        assert local.url.startswith("http://127.0.0.1:")
    finally:
        local.stop()
