"""tools/lang_scan.py: the texts of game/ for a person go through the lang file (epic #5343, #5379). Each function of
game/*.py with a plain "text" component must be a line of game/data/lang_plain.jsonl (names, record texts, owner tools)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import lang_scan  # noqa: E402

ALLOWED = lang_scan.allowed()


def test_each_plain_text_of_the_game_program_is_an_exception_of_the_data():
    seen = lang_scan.found()
    assert sorted(seen - ALLOWED) == [], "send lang.text(...) or add a line to game/data/lang_plain.jsonl"
    assert sorted(ALLOWED - seen) == [], "remove the lines of the functions with no plain text"


def test_a_new_plain_text_in_a_tellraw_fails():
    source = open(os.path.join(lang_scan.ROOT, "game", "cheats.py"), encoding="utf-8").read()
    for new in ('    g.command(f"tellraw {p} " + json.dumps({"text": "Hello"}))\n',
                "    g.command(f'tellraw {p} {{\"text\":\"Hello {p}\"}}')\n",
                "    g.command(f'tellraw {p} {{\"text\":\"{p}\"}}')\n"):
        assert lang_scan.scan(source + f"\n\ndef hello(g, p):\n{new}", "cheats") - ALLOWED == {"cheats.hello"}, new
    assert lang_scan.scan('def ok(g, p):\n    g.command("tellraw " + json.dumps({"text": "", "extra": [lang.text("k")]}))\n',
                          "m") == set()
