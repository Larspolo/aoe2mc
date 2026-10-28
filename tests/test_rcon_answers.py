"""Each RCON command gets its own answer (#3040): the client matches the request id, opens a new connection after a
timeout, and ends an answer of full 4096-character parts with an empty RESPONSE packet, as the 26.3 server needs."""
import json
import os
import shutil
import socket
import struct
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import rcon  # noqa: E402
import run  # noqa: E402


def packet(rid, text):
    body = struct.pack("<ii", rid, rcon.RESPONSE) + text.encode() + b"\0\0"
    return struct.pack("<i", len(body)) + body


def fake_server(answers, slow=()):
    """An RCON server like the 26.3 RconClient: parts of 4096 characters with the request id, "Unknown request" for
    another type, one read of at most 1460 bytes that must hold one packet. A command in slow answers after 1.5 s."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)

    def client(conn):
        with conn:
            while data := conn.recv(1460):
                size, rid, kind = struct.unpack("<iii", data[:12])
                if size != len(data) - 4:
                    return                                    # two packets in one read: the server closes
                text = data[12:-2].decode()
                if kind == rcon.LOGIN:
                    conn.sendall(packet(rid if text == "pw" else -1, ""))
                    continue
                text = answers[text] if kind == rcon.COMMAND else f"Unknown request {kind:x}"
                if data[12:-2].decode() in slow:
                    time.sleep(1.5)
                for i in range(0, max(len(text), 1), 4096):
                    conn.sendall(packet(rid, text[i:i + 4096]))

    def serve():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=client, args=(conn,), daemon=True).start()
    threading.Thread(target=serve, daemon=True).start()
    return srv.getsockname()[1]


ANSWERS = {"slow": "answer of slow", "list": "answer of list", "time": "answer of time", "if": "answer of if",
           "4096": "x" * 4096, "cjk": "漢" * 1400, "5000": "y" * 5000, "8192": "z" * 8192}


def test_each_command_gets_its_own_answer_after_a_timeout():
    with rcon.Rcon("127.0.0.1", fake_server(ANSWERS, slow={"slow"}), "pw", timeout=1) as r:
        with pytest.raises(TimeoutError):
            r.command("slow")
        time.sleep(1)                                         # the late answer arrives on the old connection
        assert [r.command(c) for c in ("list", "time", "if")] == ["answer of list", "answer of time", "answer of if"]


@pytest.mark.parametrize("cmd", ["4096", "cjk", "5000", "8192"])
def test_long_answers_come_back_whole_and_at_once(cmd):
    with rcon.Rcon("127.0.0.1", fake_server(ANSWERS), "pw", timeout=1) as r:
        t = time.time()
        assert r.command(cmd) == ANSWERS[cmd]
        assert time.time() - t < 0.5
        assert r.command("list") == "answer of list"


@pytest.mark.mc
def test_a_paper_server_gives_long_answers_whole(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        for n in (4096, 6000):
            # a list of strings in storage: each next string adds its length + 4 characters (', ' and two quotes)
            game.command(f'data modify storage aoe:t l set value [{json.dumps("a" * 1000)}]')
            while len(game.command("data get storage aoe:t l")) + 1004 < n:
                game.command(f'data modify storage aoe:t l append value {json.dumps("a" * 1000)}')
            rest = n - len(game.command("data get storage aoe:t l")) - 4
            game.command(f'data modify storage aoe:t l append value {json.dumps("a" * rest)}')
            out = game.command("data get storage aoe:t l")
            assert len(out) == n and out.endswith('"]'), (n, len(out), out[-40:])
            assert game.command("list").startswith("There are")
