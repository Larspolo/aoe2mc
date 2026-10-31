"""The tutorial and the challenges send their texts as `translate` components (#5377)."""
import json
import types

import lang  # noqa: E402

import aoe2mc
import game.challenge as challenge
import game.tutorial as tutorial  # noqa: F401  (game/ is on sys.path)


def _components(sent):
    return [json.loads(c[c.index("{"):]) for c in sent if "{" in c]


def test_tutorial_done_step_sends_the_translate_text_of_the_table(monkeypatch):
    import tutorial as t
    g = types.SimpleNamespace(sent=[], tutorial_step=0, player=1)
    g.command = g.sent.append
    monkeypatch.setattr(t, "done", lambda g, row: True)
    t.tick(g)
    key = "aoe2mc.tutorial.step_done"
    assert {"translate": key, "fallback": lang.EN_US[key], "color": "green"} in _components(g.sent)
    row = t.STEPS[1]
    assert {"translate": f"aoe2mc.tutorial.{row['name']}", "fallback": row["text"], "color": "green"} in _components(g.sent)


def test_challenge_boss_bar_sends_the_translate_text_of_the_table():
    c = next(r for r in challenge.CHALLENGES.values() if r["medal"] == "time")
    g = types.SimpleNamespace(sent=[])
    g.command = g.sent.append
    challenge.show(g, c, c["bronze"] + 1)
    key = "aoe2mc.challenge.no_medal"
    out = _components(g.sent)
    assert {"translate": key, "fallback": lang.EN_US[key]} in out
    assert {"translate": f"aoe2mc.challenge.{c['name']}", "fallback": c["goal"], "color": "yellow"} in out


def test_lang_file_has_the_step_texts_and_goals():
    en = json.loads(aoe2mc.lang_files()["assets/aoe2mc/lang/en_us.json"])
    assert all(en[f"aoe2mc.tutorial.{r['name']}"] == r["text"] for r in __import__("tutorial").STEPS)
    assert all(en[f"aoe2mc.challenge.{n}"] == r["goal"] for n, r in challenge.CHALLENGES.items())
