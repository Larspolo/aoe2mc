"""The team chats and taunts of AI scripts: chat-to-allies, chat-to-enemies, -using-id, -using-range, taunt (#5046)."""
import json
import types

import build
import diplomacy
import per
import replay
from test_bot_gather import bot_map
from test_per_up_chat import chats


def run(text, monkeypatch, seed=None):
    server, me, b = bot_map()
    sides = [b.g, types.SimpleNamespace(player=3), types.SimpleNamespace(player=4)]
    monkeypatch.setattr(build, "sides", lambda g: sides)
    monkeypatch.setattr(diplomacy, "stance", lambda g, n: "ally" if n == 3 else "enemy")
    s = per.Script(per.parse(text), b)
    if seed is not None:
        s.rng = per.np.random.default_rng(seed)
    s.step()
    return s, b, server


def test_chat_to_allies_and_enemies_reach_their_teams(monkeypatch):
    s, b, server = run('(defrule (true) => (chat-to-allies "hi") (chat-to-enemies "go") (disable-self))', monkeypatch)
    me = b.g.player
    assert chats(server) == [("@a[team=p3]", f"<Player {me}> hi"), ("@a[team=p4]", f"<Player {me}> go")]
    assert not s.warned


def test_taunt_sends_the_text_of_the_data_to_all(monkeypatch):
    s, b, server = run("(defrule (true) => (taunt 1) (disable-self))", monkeypatch)
    text = json.loads(open("game/data/taunts.jsonl").readline())["text"]
    assert [to for to, _ in chats(server)] == ["@a"] and text in chats(server)[0][1] and replay.TAUNTS["1"]
    assert not s.warned


def test_using_range_is_the_same_for_the_same_seed(monkeypatch):
    rule = "(defrule (true) => (chat-to-all-using-range 100 50) (disable-self))"
    one, two = (chats(run(rule, monkeypatch, seed=7)[2]) for _ in range(2))
    assert one == two and one[0][1].split("> ")[1].strip("<>").isdigit()


def test_no_action_of_the_list_is_unknown(monkeypatch):
    acts = ['(chat-local "a")', "(chat-local-using-id 1)", "(chat-local-using-range 1 2)", "(chat-to-all-using-id 1)",
            "(chat-to-allies-using-id 1)", "(chat-to-allies-using-range 1 2)", "(chat-to-enemies-using-id 1)",
            "(chat-to-enemies-using-range 1 2)", "(chat-to-player-using-id 2 1)", "(chat-to-player-using-range 2 1 2)",
            "(taunt-using-range 1 3)", '(chat-trace 1)', '(log "a")', '(log-trace 1)', "(trace-fact food-amount)",
            '(set-author-name "a")', '(set-author-email "a")', '(set-author-version "a")']
    s, _, _ = run("(defrule (true) => " + " ".join(acts) + " (disable-self))", monkeypatch)
    assert not s.warned
