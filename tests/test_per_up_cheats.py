"""The cheat and chat actions of AI scripts: up-cc-send-cheat, up-cc-add-resource, up-store-player-chat (#4974)."""
from test_per_rules import run
from test_per_up_chat import chats

from game import cheats, per


def code_of(resource):
    return next(c for c, e in sorted(cheats.CODES.items(), key=str) if isinstance(e, dict) and set(e) == {resource})


def script(b, text):
    s = per.Script(per.parse(text), b)
    s.step()
    return s


def test_up_cc_add_resource_needs_the_cheats():
    _, b, _ = run("(defrule (false) => (do-nothing))")
    gold = b.g.stock["gold"]
    s = script(b, "(defrule (true) => (up-cc-add-resource gold 500) (disable-self))")
    assert b.g.stock["gold"] == gold and len(s.warned) == 1     # cheats off: one warning
    b.g.cheats = True
    s = script(b, "(defrule (true) => (up-cc-add-resource gold 500) (disable-self))")
    assert b.g.stock["gold"] == gold + 500 and not s.warned


def test_up_store_player_chat_and_up_chat_data_to_all_with_percent_s():
    _, b, server = run("(defrule (false) => (do-nothing))")
    b.g.taunted = ["3", "11"]
    server.log.clear()
    s = script(b, f'(defrule (true) => (up-store-player-chat {b.g.player}) (up-chat-data-to-all "you said %s" c: 0)'
                  " (up-store-player-chat 7) (disable-self))")
    assert chats(server) == [("@a", f"<Player {b.g.player}> you said 11")]
    assert s.text == ""                                          # no chat line of player 7


def test_up_cc_send_cheat_runs_a_resource_code():
    code = code_of("wood")
    _, b, _ = run("(defrule (false) => (do-nothing))")
    b.g.cheats, wood = True, b.g.stock["wood"]
    s = script(b, f'(defrule (true) => (up-cc-send-cheat "{code}") (up-cc-send-cheat "no such code") (disable-self))')
    assert b.g.stock["wood"] == wood + cheats.CODES[code]["wood"]
    assert len(s.warned) == 1                                    # the unknown code
