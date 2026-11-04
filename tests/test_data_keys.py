"""Each key of a line of game/data/*.jsonl is read by the code of the game program (#2188). A new key needs no change
of a test line, so parallel tickets do not conflict on a list of optional keys; a misspelled key fails here."""
import glob
import os
import re

import pytest

from game import combat, table

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = "".join(open(f, encoding="utf-8").read() for f in sorted(glob.glob(os.path.join(ROOT, "game", "**", "*.py"),
                                                                          recursive=True)))


def unread(keys, code=CODE):
    """The keys that are not a string literal of the code. combat.STATS reads the Stats fields by their names."""
    return sorted(k for k in keys if k not in combat.Stats._fields and not re.search(rf"""["']{re.escape(k)}["']""", code))


def translations(keys):
    """The language columns: aoe2mc.lang_files reads "<code>" beside "en_us" and "<key>_<code>" beside "<key>" (#5436)."""
    out = set()
    for k in keys:
        m = re.fullmatch(r"(?:(.+)_)?([a-z]{2,3}_[a-z]{2})", k)
        if m and (m[1] or "en_us") in keys and k != "en_us":
            out.add(k)
    return out


@pytest.mark.parametrize("name", sorted(f for f in os.listdir(table.DIR) if f.endswith(".jsonl"))
                         + sorted(f"antiquity/{f}" for f in os.listdir(os.path.join(table.DIR, "antiquity"))))   # #3666
def test_each_key_of_a_data_file_is_read_by_the_code(name):
    keys = {k for r in table.load(name) for k in r}
    keys -= translations(keys)
    assert unread(keys) == [], name


def test_a_misspelled_key_fails_and_a_new_read_key_passes():
    assert unread({"sight", "range", "sigth"}) == ["sigth"]
    assert unread({"new_key"}) == ["new_key"]
    assert unread({"new_key"}, CODE + 'row.get("new_key")') == []



def test_a_language_column_needs_its_base_key():
    assert translations({"en_us", "de_de", "text", "text_de_de", "tip_fr_fr"}) == {"de_de", "text_de_de"}
