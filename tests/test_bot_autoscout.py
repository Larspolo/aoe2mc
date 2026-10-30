"""game/bot.py: the start scout of the bot gets the Auto Scout order at its first tick, once (#3704)."""
from test_bot_gather import bot_map

from game import bot


def counted(monkeypatch):
    """Record each call of autoscout.start (the order of the scouts) and keep the real function."""
    calls, start = [], bot.autoscout.start                             # bot imports the module as "autoscout" (sys.path)
    monkeypatch.setattr(bot.autoscout, "start", lambda g, units: (calls.append(sorted(units)), start(g, units)))
    return calls


def test_the_start_scout_explores_at_the_first_tick_and_then_not_again(monkeypatch):
    server, me, b = bot_map()
    server.entities["s0"] = {"Pos": (19.5, 64.0, 24.5), "Rotation": (0.0, 0.0)}
    b.g.soldiers["s0"] = "SCOUT_CAVALRY"
    calls = counted(monkeypatch)
    b.orders()
    assert calls == [["s0"]] and "s0" in b.g.scouting
    b.orders()
    assert calls == [["s0"]]                                           # the second tick: no new start


def test_a_bot_without_a_scout_gives_no_autoscout_order(monkeypatch):
    server, me, b = bot_map()
    calls = counted(monkeypatch)
    b.orders()
    assert calls == [[]] and not vars(b.g).get("scouting")         # start() with no unit does nothing
    assert b.scouted                                                   # the flag still ends the first tick


def test_a_civilization_scout_gets_the_order_too(monkeypatch):
    server, me, b = bot_map()
    server.entities["c0"] = {"Pos": (19.5, 64.0, 24.5), "Rotation": (0.0, 0.0)}
    b.g.soldiers["c0"] = "CAMEL_SCOUT"                                 # the Gurjaras scout (scout.SCOUTS, #2391)
    calls = counted(monkeypatch)
    b.orders()
    assert calls == [["c0"]]
