"""Chat with numbers and the text buffer of AI scripts: up-chat-data-*, up-change-name, up-store-*, up-compare-text
(#4877)."""
import json

from test_per_rules import run


def chats(server):
    return [(c.split()[1], json.loads(c.split(" ", 2)[2])["text"]) for c in server.log if c.startswith("tellraw")]


def test_up_chat_data_replaces_percent_d_by_the_value():
    s, b, server = run("""(defrule (true) => (set-goal 3 42) (up-chat-data-to-all "I have %d" g: 3)
(up-chat-data-to-player 2 "Send %d" c: 7) (up-chat-data-to-self "x %d" c: 1) (up-log-data 0 "y" c: 1) (disable-self))""")
    me = b.g.player
    assert chats(server) == [("@a", f"<Player {me}> I have 42"), ("@a[team=p2]", f"<Player {me}> Send 7")]
    assert not s.warned


def test_up_change_name_up_store_text_and_up_compare_text():
    s, b, server = run("""(defrule (true) => (up-change-name "Elon") (up-store-text "rush") (disable-self))
(defrule (up-compare-text "rush" ==) => (set-goal 1 1) (up-chat-data-to-all "plan %s" c: 0))
(defrule (up-compare-text "boom" ==) => (set-goal 2 1))""")
    assert s.goals == {1: 1}
    assert chats(server) == [("@a", "<Elon> plan rush")]


def test_up_store_player_name_gives_the_seat_name():
    s, b, server = run("(defrule (true) => (up-store-player-name 2) (disable-self))")
    assert s.text == (b.g.players.get("2", {}).get("name") or "Player 2")
