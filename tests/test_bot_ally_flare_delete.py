"""game/bot.py: an allied bot deletes its own object at the flare of the ally by taunt 69 and answers taunt 103 (#4891),
on the map of test_bot_gather (the bot is player 2, the person is player 1)."""
import combat  # noqa: E402
from test_bot_gather import bot_map

from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)

HOUSE = (10, 12, 10, 12)


def setup(monkeypatch, team=1):
    server, me, b = bot_map()
    b.g.players.setdefault("1", {})["team"] = team
    b.g.players.setdefault("2", {})["team"] = 1
    b.g.paper = True
    b.g.sites.append({"name": "HOUSE", "player": 2, "done": True, "progress": 1, "footprint": list(HOUSE)})
    sent = []
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: sent.append(c) or command(c))
    return me, b, sent


def taunt(me, n, at=(11, 64, 11)):
    me.flares = [(*at, me.clock() + 30)]
    me.taunted = [*getattr(me, "taunted", []), str(n)]


def destroyed(sent):
    return [c for c in sent if c.startswith("aoe destroy") or (c.startswith("execute as ") and c.endswith("kill @s"))]


def test_taunt_69_deletes_the_house_at_the_flare_only(monkeypatch):
    me, b, sent = setup(monkeypatch)
    taunt(me, 69)
    b.give()
    assert destroyed(sent) == [f"aoe destroy {combat.target_uuid([10, 10, 12, 12])}"]


def test_taunt_69_with_nothing_near_deletes_nothing(monkeypatch):
    me, b, sent = setup(monkeypatch)
    taunt(me, 69, at=(1, 64, 30))
    b.give()
    assert destroyed(sent) == []


def test_taunt_103_with_no_onager_gives_one_line(monkeypatch):
    me, b, sent = setup(monkeypatch)
    taunt(me, 103)
    b.give()
    assert sum("aoe2mc.bot.no_onager" in c for c in sent) == 1


def test_an_enemy_taunt_changes_nothing(monkeypatch):
    me, b, sent = setup(monkeypatch, team=2)
    taunt(me, 69)
    taunt(me, 103)
    b.give()
    assert destroyed(sent) == [] and not any("onager" in c for c in sent)
