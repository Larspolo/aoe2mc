"""Live replay: a GARRISON on an own ram puts the foot soldiers into it (Minecraft riders, transport.mount),
UNGARRISON lets them out, and the info line of the ram shows the count (#5369). Fake RCON."""
import json

import lang
import pytest
import replay
from test_replay import Fake, data
from test_replay_inspect import Server, facing

RAM = {"kind": "unit", "name": "BATTERING_RAM", "player": 1, "uuid": "ram", "ref": 60, "tile": [5.5, 10.5]}


def unit(ref, name, uuid, tile):
    return {"kind": "unit", "name": name, "player": 1, "uuid": uuid, "ref": ref, "tile": tile}


MEN = [unit(7, "MAN_AT_ARMS", "m1", [2.5, 10.5]), unit(8, "MAN_AT_ARMS", "m2", [2.5, 11.5]),
       unit(9, "KNIGHT", "k1", [2.5, 9.5]), unit(10, "VILLAGER_MALE", "v1", [3.5, 11.5])]
GARRISON = dict(time=0, player=1, kind="garrison", objects=[7, 8, 9, 10], target=60,
                names=["MAN_AT_ARMS", "MAN_AT_ARMS", "KNIGHT", "VILLAGER_MALE"])


def play(timeline, end, ai=False):
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [RAM, *MEN]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game.sent


@pytest.mark.parametrize("ai", [False, True])
def test_the_foot_soldiers_ride_the_ram_after_the_walk(ai):
    r, sent = play([GARRISON], 30000, ai)
    assert r.cargo == {60: [7, 8]} and not r.boarding
    first = "execute as ram on passengers run ride m1 mount @s"     # on the crew, the next one on the one before
    assert first in sent and "ride m2 mount m1" in sent and "tag m2 add aoe2mc.garrisoned" in sent
    assert not any(c.startswith(("ride k1", "ride v1", "tag k1", "tag v1")) for c in sent)   # no horse, no villager
    assert ("aoe hide @a m1" in sent) == ai
    assert any(c.startswith(("tp m1", "aoe moveto m1")) for c in sent[:sent.index(first)])   # it walked there first
    assert lang.plain(r.task(7)) == "garrisoned"


@pytest.mark.parametrize("ai", [False, True])
def test_ungarrison_lets_them_out_next_to_the_ram(ai):
    r, sent = play([GARRISON, dict(time=20000, player=1, kind="ungarrison", objects=[60])], 30000, ai)
    assert r.cargo == {}
    assert "ride m1 dismount" in sent and "tag m2 remove aoe2mc.garrisoned" in sent
    assert ("aoe show @a m2" in sent) == ai
    ram = r.units[60].cell
    for i in (7, 8):
        assert max(abs(a - b) for a, b in zip(r.units[i].cell, ram)) <= 3 * r.T


def test_a_full_ram_takes_no_more():
    rows = [unit(7 + k, "MAN_AT_ARMS", f"m{k}", [2.5, 8.5 + k]) for k in range(6)]
    d = data([dict(time=0, player=1, kind="garrison", objects=[u["ref"] for u in rows], target=60,
                   names=["MAN_AT_ARMS"] * 6), dict(time=30000, player=1, kind="chat", text="end")])
    d["objects"] += [RAM, *rows]
    now = [0.0]
    r = replay.Replay(Fake(), d)
    r.run(clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None)
    assert len(r.cargo[60]) == 4                                     # the garrison of a battering ram (carriers.jsonl)


@pytest.mark.parametrize("holder, name, fits", [
    ("BATTERING_RAM", "MAN_AT_ARMS", True), ("BATTERING_RAM", "ARCHER", True), ("BATTERING_RAM", "KNIGHT", False),
    ("BATTERING_RAM", "VILLAGER_MALE", False), ("TRANSPORT_SHIP", "KNIGHT", True),
    ("TRANSPORT_SHIP", "BATTERING_RAM", True), ("TRANSPORT_SHIP", "VILLAGER_MALE", True),
    ("SIEGE_TOWER", "VILLAGER_MALE", True), ("SIEGE_TOWER", "KNIGHT", False),
])
def test_which_units_fit_as_in_the_game_program(holder, name, fits):
    assert replay.Replay.fits(holder, name) == fits


def test_the_info_line_of_the_ram_shows_the_count():
    d = data([])
    d["objects"] = [dict(RAM, uuid="1dcc6967-173c-2031-ccae-9650ba134730"), *MEN[:2]]
    r = replay.Replay(Server(), d)
    r.grid()
    r.units[60].pos = (26.0, 70.0, 30.0)
    r.cargo = {60: [7, 8]}
    facing(r, 40.0)
    (c,) = [c for c in r.inspect(10000, clock=lambda: 0.0) if " actionbar " in c]
    text = "".join(lang.plain(p) for p in json.loads(c.split(" actionbar ", 1)[1]))
    assert text.startswith(replay.pretty("BATTERING_RAM")) and text.endswith(" · garrison 2")
