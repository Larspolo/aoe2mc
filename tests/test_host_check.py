"""tools/host_check.py (#5916): the argument parsing and the form of result.json, with no server."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import host_check  # noqa: E402
import rejoin_check  # noqa: E402


def test_parse():
    a = host_check.parse(["W", "OUT", "--speed", "2", "--beat", "7"])
    assert (a.world, a.out, a.speed, a.beat) == ("W", "OUT", 2.0, 7)
    assert host_check.parse(["W", "OUT"]).speed == 4.0


def test_line():
    m = host_check.LINE.search("Join the server 10.0.0.5:25601 (other computers on the network).")
    assert m.groups() == ("10.0.0.5", "25601")


def ok_args():
    return (("10.0.0.5", "25601"), 25601, "http://10.0.0.5:25602/resources.zip", ["10.0.0.5"],
            "Test passed", ["Disconnecting eve (/10.0.0.5:5): You are not white-listed on this server!"], False, [],
            (True, ["Unknown or incomplete command, see below for error"], ["Controls: ..."]), True)


def test_result_ok(tmp_path):
    r = host_check.result(*ok_args())
    assert r and all(ok for ok, _ in r.values()) and all(isinstance(d, str) for _, d in r.values())
    exits = []
    rejoin_check.os._exit, old = exits.append, rejoin_check.os._exit
    try:
        rejoin_check.done(r, str(tmp_path))
    finally:
        rejoin_check.os._exit = old
    assert exits == [0]
    data = json.load(open(tmp_path / "result.json"))
    assert set(data) == set(r) and all(len(v) == 2 for v in data.values())


@pytest.mark.parametrize("i,value", [(0, ("localhost", "25601")), (3, ["127.0.0.1"]), (4, ""), (5, []), (6, True),
                                             (8, (False, ["Unknown or incomplete command"], ["x"])), (8, (True, [], ["x"])),
                                             (8, (True, ["Unknown or incomplete command"], []))])
def test_result_fail(i, value):
    args = list(ok_args())
    args[i] = value
    assert not all(ok for ok, _ in host_check.result(*args).values())


def test_servers_dat(tmp_path):
    import mc_shot
    import nbtlib
    mc_shot.servers_dat(tmp_path / "servers.dat", "10.0.0.5:25601")
    s = nbtlib.load(tmp_path / "servers.dat", gzipped=False)["servers"]
    assert [(str(x["ip"]), int(x["acceptTextures"])) for x in s] == [("10.0.0.5:25601", 1)]
