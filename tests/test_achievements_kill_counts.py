"""The "count:kill" achievements (#5641): the grant comes when the kills of the line reach its need, once per player."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402
import build  # noqa: E402

ROWS = [{"name": "TREBS", "event": "count:kill", "by": ["TREBUCHET"], "need": 3},
        {"name": "DARK_MILITIA", "event": "count:kill", "killed": ["villagers"], "by": ["MILITIA"], "need": 2, "age": 0},
        {"name": "SHU_GUARDS", "event": "count:kill", "by": ["WHITE_FEATHER_GUARD"], "need": 1, "civ": "SHU"}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"


def game(civ="FRANKS", share=None, techs=()):
    sent = []
    return SimpleNamespace(player=1, share=share, command=sent.append, techs=set(techs),
                           data={"players": {"1": {"civ": civ}}}), sent


def test_grant_at_the_need_and_once(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for _ in range(2):
        achievements.killed(g, "ARCHER", "TREBUCHET")
    assert sent == []
    achievements.killed(g, "CASTLE", "TREBUCHET")
    assert sent == [GRANT + "trebs"]
    achievements.killed(g, "ARCHER", "TREBUCHET")
    assert sent == [GRANT + "trebs"] and g.kill_counts["TREBS"] == 4


def test_other_killers_victims_and_civs_do_not_count(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for victim, by in (("ARCHER", "MANGONEL"), ("ARCHER", "MILITIA"), ("ARCHER", "MILITIA"),
                       ("VILLAGER_MALE", "MILITIA"), ("ARCHER", "WHITE_FEATHER_GUARD")):
        achievements.killed(g, victim, by)
    assert sent == []
    g, sent = game("SHU")
    achievements.killed(g, "ARCHER", "WHITE_FEATHER_GUARD")
    assert sent == [GRANT + "shu_guards"]


def test_the_age_limit(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    achievements.killed(g, "VILLAGER_MALE", "MILITIA")
    g.techs.add(build.AGE_TECHS[0])                                   # the Feudal Age
    achievements.killed(g, "VILLAGER_FEMALE", "MILITIA")
    assert sent == []
    g.techs.clear()
    achievements.killed(g, "VILLAGER_FEMALE", "MILITIA")
    assert sent == [GRANT + "dark_militia"]


def test_no_grant_for_a_bot(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game("SHU", share=object())
    for _ in range(3):
        achievements.killed(g, "ARCHER", "TREBUCHET")
        achievements.killed(g, "ARCHER", "WHITE_FEATHER_GUARD")
    assert sent == []
