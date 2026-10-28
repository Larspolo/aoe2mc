"""game/: the RCON client against a fake server, and the game program on a real server (marker mc, #137)."""
import os
import re
import shutil
import socket
import struct
import threading

import pytest

from game import rcon, run


def fake_server(answers):
    """An RCON server on localhost that accepts the password "pw" and answers commands from a dict."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def serve():
        conn, _ = srv.accept()
        with conn:
            while head := conn.recv(12):
                size, rid, kind = struct.unpack("<iii", head)
                text = conn.recv(size - 8)[:-2].decode()
                if kind == rcon.LOGIN:
                    rid, text = (rid if text == "pw" else -1), ""
                elif kind != rcon.COMMAND:                         # like the server: an end mark of the client
                    text = f"Unknown request {kind:x}"
                else:
                    text = answers[text]
                for i in range(0, max(len(text), 1), 4096):       # like the server: packets of 4096 bytes
                    body = struct.pack("<ii", rid, rcon.RESPONSE) + text[i:i + 4096].encode() + b"\0\0"
                    conn.sendall(struct.pack("<i", len(body)) + body)
        srv.close()
    threading.Thread(target=serve, daemon=True).start()
    return srv.getsockname()[1]


def test_rcon_sends_commands_and_joins_long_answers():
    port = fake_server({"list": "There are 0 of a max of 20 players online: ", "long": "x" * 5000})
    with rcon.Rcon("127.0.0.1", port, "pw") as r:
        assert r.command("list").startswith("There are 0")
        assert r.command("long") == "x" * 5000
        assert r.command("list").startswith("There are 0")         # still in step after the long answer


def test_rcon_wrong_password():
    with pytest.raises(rcon.RconError, match="login failed"):
        rcon.Rcon("127.0.0.1", fake_server({}), "wrong")


def test_players_play_in_creative_mode_on_a_local_server():
    props = dict(line.split("=", 1) for line in run.properties(25565, 25575, "pw").splitlines())
    assert props["gamemode"] == "creative" and props["force-gamemode"] == "true"
    assert props["server-ip"] == "127.0.0.1"                        # only local players can join and get op


def test_a_player_who_joins_gets_operator_rights():
    sent = []
    game = run.Game(".")
    game.rcon = type("R", (), {"command": lambda self, c: sent.append(c) or ""})()
    game.server = type("S", (), {"log": [
        "[21:44:16] [Server thread/INFO]: Larspolo joined the game",
        "[21:44:20] [Server thread/INFO]: <Larspolo> Bob joined the game",          # chat: no op
        "[21:44:21] [Server thread/INFO]: Larspolo[/127.0.0.1:50000] logged in with entity id 1"]})()
    game.op_joined()
    game.server.log.append("[21:45:00] [Server thread/INFO]: Alex_2 joined the game")
    game.op_joined()
    game.op_joined()
    assert sent == ["op Larspolo", "op Alex_2"]                     # each join once


def position(game):
    m = re.search(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]", game.command("data get entity @e[tag=t137,limit=1] Pos"))
    return tuple(map(float, m.groups())) if m else None


def test_properties_let_players_join():
    props = dict(line.split("=", 1) for line in run.properties(25565, 25575, "pw").splitlines())
    assert props["white-list"] == "false" and props["online-mode"] == "false"
    assert (props["server-port"], props["rcon.port"], props["rcon.password"]) == ("25565", "25575", "pw")


@pytest.mark.mc
def test_game_moves_a_unit_with_tp(tiny_world, tmp_path):
    import time

    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        with open(os.path.join(game.folder, "server.properties")) as f:      # the server keeps the values (#292)
            props = f.read()
        assert "gamemode=creative" in props and "force-gamemode=true" in props
        assert "white-list=false" in props.splitlines()
        game.forceload()
        end = time.time() + 60                      # entities load in other threads
        while "Added tag" not in game.command("tag @e[nbt={NoAI:1b},limit=1] add t137"):
            assert time.time() < end, "no unit in the world"
            time.sleep(1)
        x, y, z = position(game)
        game.command(f"tp @e[tag=t137,limit=1] {x + 2} {y} {z - 1}")
        x2, _, z2 = position(game)
        assert (x2, z2) == pytest.approx((x + 2, z - 1))
        print(f"{run.bench(game, 500):.0f} commands per second through RCON")
