"""
A small RCON client (Source RCON protocol, as the vanilla Minecraft server speaks it). Standard library only.

A packet is: int32 length, int32 request id, int32 type, ASCII payload, two zero bytes (little-endian).
Types: 3 = login, 2 = command, 0 = response. A failed login answers with request id -1.
The server splits an answer into parts of 4096 characters (UTF-16 units, sent as UTF-8) and sends no end mark: after a
full part, the client sends an empty RESPONSE packet, and the "Unknown request" answer to it marks the end (#3040).
Each answer has the request id of its command: the client drops the late answers of a command that timed out.
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
        self.addr, self.password, self.timeout, self.id, self.sock = (host, port), password, timeout, 0, None
        self._connect(retry)

    def _connect(self, retry=0):
        end = time.time() + retry
        while True:
            try:
                self.sock = socket.create_connection(self.addr, timeout=self.timeout)
                break
            except OSError:
                if time.time() > end:
                    raise
                time.sleep(0.5)
        if self._request(LOGIN, self.password)[0] == -1:
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

    def _send(self, kind, payload):
        self.id += 1
        body = struct.pack("<ii", self.id, kind) + payload.encode("utf-8") + b"\0\0"
        self.sock.sendall(struct.pack("<i", len(body)) + body)
        return self.id

    def _part(self, *rids):
        """The next packet with one of the ids rids (or -1, a failed login): the late answers of older ids go away."""
        while True:
            rid, part = self._packet()
            if rid in rids or rid == -1:
                return rid, part

    def _request(self, kind, payload):
        if self.sock is None:                 # the last command timed out: its stream is not safe (#3040)
            self._connect()
        try:
            rid = self._send(kind, payload)
            got, data = self._part(rid)
            if kind == COMMAND and len(data.decode("utf-8").encode("utf-16-le")) == 2 * 4096:
                end = self._send(RESPONSE, "")    # after the first part: the server reads it alone
                while (part := self._part(rid, end))[0] == rid:
                    data += part[1]
        except (OSError, RconError):
            self.close()
            raise
        return got, data.decode("utf-8")

    def command(self, cmd):
        """Send one command (without "/") and return the answer of the server. A command longer than MAX bytes is an
        error before it goes out: the server would close the connection (#1647)."""
        if (n := len(cmd.encode("utf-8"))) > MAX:
            raise RconError(f"RCON command of {n} bytes, the limit is {MAX}: {cmd[:80]}...")
        return self._request(COMMAND, cmd)[1]

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
