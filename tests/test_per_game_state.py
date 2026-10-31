"""game/per.py: the facts of the players and of the game state, and clear-tribute-memory (#5045). The map of
test_bot_gather: player 1 (a person) and the bot, player 2; they are enemies (no team)."""
from test_bot_gather import bot_map

from game import conquest, per
from game.bot import build, train  # noqa: F401  (the modules that per uses)

FACTS = [("player-computer", 2), ("player-human", 1), ("player-in-game", 1), ("player-number", 1),
         ("player-resigned", 2), ("player-valid", 1), ("players-score", 1, ">=", 0), ("current-score", ">=", 0),
         ("players-tribute", 1, "gold", ">=", 0), ("cheats-enabled",), ("game-type", "==", 0),
         ("fe-sub-game-type", "==", 0), ("starting-resources", ">=", 0), ("victory-condition", "standard"),
         ("town-under-attack",), ("hold-relics",), ("hold-koh-ruin",), ("enemy-captured-relics",),
         ("wall-invisible-percentage", "==", 0)]


def script(text=""):
    server, me, b = bot_map()
    me.bots = [b]                                                      # run.py: player 1 holds the bots
    for o in b.g.data["objects"]:
        o.setdefault("player", 0)
    return per.Script(per.parse(text), b), b, me


def test_human_computer_and_resigned():
    s, b, me = script()
    assert s.check(("player-human", 1)) and not s.check(("player-computer", 1))
    assert s.check(("player-computer", 2)) and not s.check(("player-resigned", 2))
    assert s.check(("game-type", "==", 0))
    conquest.defeat(b.g, 2)
    assert s.check(("player-resigned", 2)) and not s.check(("player-in-game", 2))


def test_tribute_memory(monkeypatch):
    s, b, me = script()
    import diplomacy as plain  # game/ modules import it by its plain name
    monkeypatch.setattr(plain.market, "markets", lambda g: [1])
    me.stock["gold"] = 1000
    assert plain.send(me, None, 2, "gold")
    assert s.check(("players-tribute", 1, "gold", ">=", 100))
    s.act(None, ("clear-tribute-memory",))
    assert not s.check(("players-tribute", 1, "gold", ">=", 100))


def test_no_fact_is_unknown(capsys):
    s, b, me = script()
    for f in FACTS:
        s.check(f)
    assert "unknown" not in capsys.readouterr().err
