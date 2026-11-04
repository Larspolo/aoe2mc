"""The achievements of a count of buildings, a list of events, a queue and a policy (#5642)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402

ROWS = [{"name": "PASTURED", "event": "count:build", "buildings": ["PASTURE"], "need": 3, "civ": "KHITANS"},
        {"name": "POSTED", "event": "count:build", "buildings": ["OUTPOST"], "by": ["CHAMPI_WARRIOR"], "need": 2},
        {"name": "TC_UP", "event": ["research ECONOMIC_TOWN_CENTER", "research MILITARY_TOWN_CENTER"]},
        {"name": "SPURS", "event": "research FLEMISH_REVOLUTION", "villagers": 3},
        {"name": "BOOM", "event": "count:queue", "units": ["VILLAGER_MALE"], "need": 3, "ages": 0},
        {"name": "POLITICS", "event": "policy", "civ": "KHITANS"}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"


def game(civ="KHITANS", share=None, villagers=0):
    sent = []
    return SimpleNamespace(player=1, share=share, command=sent.append, villagers=dict.fromkeys(range(villagers)),
                           data={"players": {"1": {"civ": civ}}}), sent


def test_each_event_grants_at_its_count_once(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(villagers=3)
    for _ in range(2):
        achievements.built(g, "PASTURE", ["VILLAGER"])
    achievements.built(g, "OUTPOST", ["CHAMPI_WARRIOR", "CHAMPI_WARRIOR"])
    achievements.built(g, "OUTPOST", ["VILLAGER"])
    assert sent == []                                  # one building before each count
    achievements.built(g, "PASTURE")
    achievements.built(g, "OUTPOST", ["CHAMPI_WARRIOR"])
    achievements.built(g, "PASTURE")
    q = [{"name": "VILLAGER_MALE"}] * 2
    achievements.queued(g, q, 0)
    assert sent == [GRANT + "pastured", GRANT + "posted"]  # one villager before the count
    achievements.queued(g, q + q[:1], 0)
    for name in ("research MILITARY_TOWN_CENTER", "research FLEMISH_REVOLUTION", "policy", "policy"):
        achievements.event(g, g, name)
    assert sent[2:] == [GRANT + k for k in ("boom", "tc_up", "spurs", "politics")]


def test_no_grant_for_another_civ_age_few_villagers_or_a_bot(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(civ="FRANKS", villagers=2)
    for _ in range(3):
        achievements.built(g, "PASTURE")
    achievements.queued(g, [{"name": "VILLAGER_MALE"}] * 3, 1)
    for name in ("policy", "research FLEMISH_REVOLUTION", "research LOOM"):
        achievements.event(g, g, name)
    assert sent == []
    bot, sent = game(share=g, villagers=3)
    for _ in range(3):
        achievements.built(bot, "PASTURE")
    achievements.queued(bot, [{"name": "VILLAGER_MALE"}] * 3, 0)
    achievements.event(bot, bot, "research ECONOMIC_TOWN_CENTER")
    assert sent == []
