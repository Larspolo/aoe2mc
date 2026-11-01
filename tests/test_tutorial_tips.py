"""The tip of a tutorial step comes in the chat after the step is done, not before (#5505)."""
import json
import types

import tutorial as t  # game/ is on sys.path

import aoe2mc


def _tips(sent):
    return [json.loads(c[c.index("{"):]) for c in sent if "tip_" in c]


def _g():
    g = types.SimpleNamespace(sent=[], player=1)
    g.command = g.sent.append
    return g


def test_no_tip_before_the_step_is_done(monkeypatch):
    g = _g()
    monkeypatch.setattr(t, "done", lambda g, row: False)
    t.tick(g)
    assert g.tutorial_step == 0 and not _tips(g.sent)


def test_the_tip_comes_after_the_step_is_done(monkeypatch):
    g = _g()
    g.tutorial_step = 0
    row = t.STEPS[0]
    monkeypatch.setattr(t, "done", lambda g, row: True)
    monkeypatch.setitem(row, "tip", "a tip")
    t.tick(g)
    tip = {"translate": f"aoe2mc.tutorial.tip_{row['name']}", "fallback": "a tip", "color": "gray"}
    assert _tips(g.sent) == [tip] and g.tutorial_step == 1


def test_a_step_without_a_tip_sends_none(monkeypatch):
    g = _g()
    g.tutorial_step = 0
    monkeypatch.setattr(t, "done", lambda g, row: True)
    monkeypatch.delitem(t.STEPS[0], "tip", raising=False)
    t.tick(g)
    assert not _tips(g.sent)


def test_the_lang_file_has_the_tips():
    en = json.loads(aoe2mc.lang_files()["assets/aoe2mc/lang/en_us.json"])
    assert all(en[f"aoe2mc.tutorial.tip_{r['name']}"] == r["tip"] for r in t.STEPS if "tip" in r)
