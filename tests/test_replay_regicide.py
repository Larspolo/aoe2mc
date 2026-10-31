"""Live replay of a Regicide record: the King of each player, and the player is out when its King dies (#4835).
Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import regicide  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402

KING = regicide.MODES["regicide"]["units"][0]
UUIDS = {1: "1dcc6967-173c-2031-ccae-9650ba134731", 2: "1dcc6967-173c-2031-ccae-9650ba134732"}


class Server(Fake):
    """A fake server where only the Kings of the players in `alive` live."""
    def __init__(self, alive):
        super().__init__()
        self.alive = alive

    def command(self, cmd):
        super().command(cmd)
        return "Test passed" if any(f"tag=aoe2mc.p{p}," in cmd for p in self.alive) else "Test failed"


def kings(kind, game=None):
    d = data([])
    d["lobby"] = {"type": kind, "dataset": "Definitive Edition"}
    d["objects"] = [{"kind": "unit", "name": KING, "player": p, "tile": [4.5 + 6 * p, 6.5], "uuid": u, "ref": 10 + p}
                    for p, u in UUIDS.items()]
    return replay.Replay(game or Fake(), d)


def texts(cmds):
    """The plain text of each tellraw, title and panel name command."""
    out = []
    for c in cmds:
        if c.startswith(("tellraw", "title @a title", "scoreboard players display name")):
            j = json.loads(c[min(i for i in (c.find("{"), c.find("[")) if i >= 0):])
            out.append("".join(lang.plain(t) for t in (j if isinstance(j, list) else [j])))
    return out


def summary(r):
    return [t for t in texts(r.summary_commands()) if "King killed" in t]


def test_the_delete_of_a_king_puts_its_player_out():
    r = kings(replay.REGICIDE)
    assert r.kings == {1: {UUIDS[1]}, 2: {UUIDS[2]}}
    assert f"tag {UUIDS[2]} add {regicide.KING}" in r.king_tags()
    cmds = r.commands(delete(65000, [12], names=[KING], player=2))
    assert f"kill {UUIDS[2]}" in cmds
    assert "Player 2 (Aztecs) is out" in texts(cmds)
    assert r.regicided == {2: 65000}
    assert summary(r) == ["Player 2 (Aztecs): King killed 01:05 (Regicide)"]
    assert "01:05 King killed" in "".join(map(lang.plain, json.loads(r.timeline_commands(10 ** 6)[0].split("=", 1)[1][:-1])["pages"]))       # the Timeline book


def test_a_king_that_died_in_a_fight_puts_its_player_out():
    r = kings(replay.REGICIDE, Server(alive={1}))
    assert r.king_check(90000) and r.regicided == {2: 90000}
    assert r.king_check(91000) == []                        # once
    panel = " ".join(texts(r.score_commands()))
    assert "Player 2 (Aztecs) · King killed" in panel and "Player 1 (Britons) · King ·" in panel


def test_the_same_death_in_a_random_map_game_puts_no_player_out():
    r = kings("Random Map", Server(alive={1}))
    assert r.kings == {} and r.king_tags() == []
    cmds = r.commands(delete(65000, [12], names=[KING], player=2))
    assert f"kill {UUIDS[2]}" in cmds and r.king_check(90000) == []
    assert r.regicided == {} and summary(r) == []
    assert "King" not in " ".join(texts(r.score_commands()))
