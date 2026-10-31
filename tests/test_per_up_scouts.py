"""up-send-scout and up-reset-scouts of an AI script (#4969). The map of test_bot_gather: 32 × 32 tiles (tile size 1),
the town center of the bot (player 2) at tile (21, 21)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses


def script(text):
    server, me, b = bot_map()
    me.bots = [b]
    b.g.soldiers["sc"] = "SCOUT_CAVALRY"
    b.g.soldiers["m1"] = "MILITIA"
    server.entities["sc"] = {"Pos": (21.5, 64.0, 21.5), "Rotation": (0.0, 0.0)}
    return per.Script(per.parse(text), b), b, server


def test_the_scout_walks_to_the_point_and_stops(capsys):
    s, b, server = script("(defrule (true) => (up-send-scout group-type-land-explore scout-opposite) (disable-self))")
    s.step()
    walks = [c for c in server.log if c.startswith("aoe moveto")]
    assert walks == [f"aoe moveto sc 10 {b.g.map.y(10, 10)} 10"]   # opposite of (21, 21): tile (10, 10)
    assert s.scouts == ["sc"]
    s.act(None, ("up-reset-scouts",))
    assert "aoe stop sc" in server.log and s.scouts == []
    s.act(None, ("up-send-scout", "group-type-water-explore", "scout-center"))
    s.act(None, ("up-send-scout", "group-type-land-explore", "scout-nowhere"))
    err = capsys.readouterr().err
    assert "group type group-type-water-explore" in err and "scout method scout-nowhere" in err


def test_no_explorers_send_no_scout():
    s, b, server = script("(defrule (true) => (set-strategic-number sn-total-number-explorers 0)"
                          " (up-send-scout group-type-land-explore scout-center))")
    s.step()
    assert not [c for c in server.log if c.startswith("aoe moveto")] and s.scouts == []
