"""The spectator chooses the player of the view in the live replay (#1303): `run.py --replay --view N` and the menu item
"View" (game/replay_input.py VIEW) go through all players and back to "all players". Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
import replay_input as ri  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_fog_units import ENEMY  # noqa: E402
from test_replay_input import Scores, poll  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

from game import run  # noqa: E402

CHAT = [dict(time=5000, player=1, kind="chat", text="hi")]


def fog(cmds):
    return [c for c in cmds if c.startswith(("aoe hide", "aoe show"))]


def test_the_view_option_starts_the_replay_with_the_view_of_a_player(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    got = []

    class Game(Fake):
        def __init__(self, *a, **kw):
            super().__init__()
            self.port = self.game_port = 0

        def start(self):
            pass

        def stop(self):
            pass

    def eof(prompt=""):
        raise EOFError
    monkeypatch.setattr(run, "Game", Game)
    monkeypatch.setattr(run, "replay", lambda *a, **kw: got.append(kw.get("view")))
    monkeypatch.setattr("builtins.input", eof)
    for argv, want in (([], None), (["--view", "2"], 2), (["--view", "0"], None)):
        run.main([str(tmp_path), "--replay", *argv])
        assert got[-1] == want, argv
    d = data(CHAT)
    d["objects"] += [VIL, ENEMY]
    game, now = Fake(), [0.0]
    replay.Replay(game, d, pov=2).run(clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None)
    assert fog(game.sent) == ["aoe hide @a u1"]                      # the villager of player 1 is out of sight


def test_a_click_on_view_goes_to_each_player_and_back_to_all_players():
    game = Scores()
    control = {"speed": 1.0, "paused": False, "time": 0, "view": None,
               "players": {1: ("Player 1 (Britons)", "blue"), 2: ("Player 2 (Aztecs)", "gold")}}
    inp = ri.Input(game, clock=lambda: poll.t)
    views, said = [], []
    for _ in range(3):
        game.scores["anna"]["aoe_replay"] = ri.VIEW                   # /trigger aoe_replay set VIEW, or the menu
        poll.t += 1
        n = len(game.sent)
        inp(control)
        views.append(control["view"])
        said += [json.loads(c.split(" ", 2)[2]) for c in game.sent[n:] if c.startswith("tellraw @a ")]
    assert views == [1, 2, None]
    assert said == [{"text": "View: Player 1 (Britons)", "color": "blue"},
                    {"text": "View: Player 2 (Aztecs)", "color": "gold"}, {"text": "View: all players", "color": "white"}]


def test_the_menu_item_names_the_view_and_changes_with_a_click():
    game = Scores()
    control = {"speed": 1.0, "paused": False, "time": 0, "view": None, "players": {2: ("Player 2 (Aztecs)", "gold")}}
    game.click("ben", ri.MENU)
    inp = poll(game, control)
    menus = [c for c in game.sent if c.startswith("aoe menu ben Replay ")]
    assert len(menus) == 1 and "15:spyglass:View%3A%20all%20players" in menus[0]
    game.scores["ben"]["aoe_menu"] = 15 + 1                          # the slot of "View"
    poll.t += 1
    inp(control)
    menus = [c for c in game.sent if c.startswith("aoe menu ben Replay ")]
    assert control["view"] == 2 and len(menus) == 2 and "View%3A%20Player%202%20%28Aztecs%29" in menus[1]


def test_all_players_again_shows_the_hidden_units():
    d = data(CHAT + [dict(time=9000, player=1, kind="chat", text="gg")])
    d["objects"] += [VIL, ENEMY]
    game, now = Fake(), [0.0]

    def poll_(control):                                              # the spectator clicks "View" after 7 s
        if control["time"] >= 7000 and control["view"] is not None:
            assert control["players"] == {1: ("Player 1 (Britons)", "blue"), 2: ("Player 2 (Aztecs)", "gold")}
            ri.apply(ri.VIEW, control)                               # player 1 -> player 2
            ri.apply(ri.VIEW, control)                               # player 2 -> all players
    r = replay.Replay(game, d, pov=1)
    r.run(clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, poll=poll_)
    assert fog(game.sent) == ["aoe hide @a u2", "aoe show @a u2"] and r.pov is None and not r.hidden


def test_a_jump_back_keeps_the_view():
    d = data(CHAT)
    made = []

    def make():
        made.append(replay.Replay(Fake(), d, pov=1))
        return made[-1]

    def poll_(control):
        if len(made) == 1 and control["time"] >= 3000:
            ri.apply(ri.VIEW, control)                               # player 1 -> player 2
            control["jump"] = 1000                                   # then back 2 s: a fresh replay
    now = [0.0]
    replay.live(make, restart=lambda: None, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s),
                log=None, poll=poll_)
    assert len(made) == 2 and made[1].pov == 2
