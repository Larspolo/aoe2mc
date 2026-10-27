"""
A small RCON client (Source RCON protocol, as the vanilla Minecraft server speaks it). Standard library only.

A packet is: int32 length, int32 request id, int32 type, ASCII payload, two zero bytes (little-endian).
Types: 3 = login, 2 = command, 0 = response. A failed login answers with request id -1.
The server splits an answer into packets of at most 4096 bytes.
"""
import socket
import struct
import time

LOGIN, COMMAND, RESPONSE = 3, 2, 0
MAX = 1446             # bytes of one command (packet size 1460 minus the header): the server closes the connection after a longer one


class RconError(Exception):
    pass


class Rcon:
    def __init__(self, host, port, password, timeout=10, retry=30):
        """Connect and log in. retry: seconds to try again while the server does not listen yet."""
        end = time.time() + retry
        while True:
            try:
                self.sock = socket.create_connection((host, port), timeout=timeout)
                break
            except OSError:
                if time.time() > end:
                    raise
                time.sleep(0.5)
        self.id = 0
        if self._request(LOGIN, password)[0] == -1:
            self.close()
            raise RconError("RCON login failed (wrong password)")

    def _recv(self, n):
        data = b""
        while len(data) < n:
            part = self.sock.recv(n - len(data))
            if not part:
                raise RconError("the server closed the RCON connection")
            data += part
        return data

    def _packet(self):
        size, = struct.unpack("<i", self._recv(4))
        rid, _ = struct.unpack("<ii", self._recv(8))
        return rid, self._recv(size - 8)[:-2]

    def _request(self, kind, payload):
        self.id += 1
        body = struct.pack("<ii", self.id, kind) + payload.encode("utf-8") + b"\0\0"
        self.sock.sendall(struct.pack("<i", len(body)) + body)
        rid, part = self._packet()
        data = part
        while len(part) >= 4096:              # a long answer continues in the next packet
            part = self._packet()[1]
            data += part
        return rid, data.decode("utf-8")

    def command(self, cmd):
        """Send one command (without "/") and return the answer of the server. A command longer than MAX bytes is an
        error before it goes out: the server would close the connection (#1647)."""
        if (n := len(cmd.encode("utf-8"))) > MAX:
            raise RconError(f"RCON command of {n} bytes, the limit is {MAX}: {cmd[:80]}...")
        return self._request(COMMAND, cmd)[1]

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
