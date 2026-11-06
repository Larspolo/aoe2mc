"""--address and --port of a --host game (#5914): the pack URL has the given address and the fixed ports."""
import os
import subprocess
import sys
import urllib.request

from game import run
from tools import mc_check


def test_pack_url_has_address_and_fixed_port(tmp_path):
    path = tmp_path / "resources.zip"
    path.write_bytes(b"pack")
    port = mc_check.free_port()
    pack = run.pack_source(str(path), host=True, address="203.0.113.7", port=port)
    try:
        assert pack.url == f"http://203.0.113.7:{port}/resources.zip"
        assert urllib.request.urlopen(f"http://127.0.0.1:{port}/resources.zip").read() == b"pack"
    finally:
        pack.stop()


def test_no_address_uses_network_address(tmp_path, monkeypatch):
    path = tmp_path / "resources.zip"
    path.write_bytes(b"pack")
    monkeypatch.setattr(run, "network_address", lambda: "192.168.5.9")
    pack = run.pack_source(str(path), host=True)
    try:
        assert pack.url.startswith("http://192.168.5.9:")
    finally:
        pack.stop()


def test_help_has_options():
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "game", "run.py"), "--help"],
                         capture_output=True, text=True).stdout
    assert "--address HOST" in out and "--port N" in out
