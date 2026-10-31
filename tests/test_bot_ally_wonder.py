"""game/bot.py: an allied bot puts a wonder first in its build order by taunt 37 (#4884), on the map of
test_bot_gather (the bot is player 2, the person is player 1)."""
from test_bot_gather import bot_map

from game.bot import WAIT, build  # noqa: F401  (puts game/ on the path for the plain names)


def setup(monkeypatch, imperial, ally=True):
    server, me, b = bot_map()
    for p, t in (("1", 1), ("2", 1 if ally else 2)):
        b.g.players.setdefault(p, {})["team"] = t
    monkeypatch.setattr(build, "ages", lambda g: 3 if imperial else 2)
    b.g.stock.update(food=9999, wood=9999, gold=9999, stone=9999)
    sent = []
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: sent.append(c) or command(c))
    me.taunted = ["37"]
    b.give()
    b.build()
    return b, sent


def wonders(b):
    return [s for s in b.g.sites if s["name"] == "WONDER"]


def test_imperial_age_gives_a_wonder_site(monkeypatch):
    b, sent = setup(monkeypatch, imperial=True)
    assert len(wonders(b)) == 1
    assert not any(WAIT["37"] in c for c in sent)


def test_before_the_imperial_age_answers_and_builds_no_wonder(monkeypatch):
    b, sent = setup(monkeypatch, imperial=False)
    assert not wonders(b) and b.order[0] == "WONDER"
    assert sum(WAIT["37"] in c for c in sent) == 1


def test_enemy_taunt_changes_nothing(monkeypatch):
    b, sent = setup(monkeypatch, imperial=True, ally=False)
    assert not wonders(b) and b.order[0] != "WONDER"
