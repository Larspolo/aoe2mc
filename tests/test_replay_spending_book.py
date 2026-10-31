"""Live replay: each viewer gets a written book "Spending" at the end, the spent resources of each player on its own page,
by group with its share of the total (#4392, item 4 of #4386)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import build  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
from test_replay import Fake, data  # noqa: E402

PREFIX = "give @a minecraft:written_book[minecraft:written_book_content="


def text(page):
    """The plain text of a page component (the heading has a color, #1643)."""
    return page["text"] + "".join(text(e) for e in page.get("extra", []))


def book(cmds):
    assert len(cmds) == 1 and cmds[0].startswith(PREFIX) and cmds[0].endswith("]")
    b = json.loads(cmds[0][len(PREFIX):-1])
    return {**b, "pages": [text(p) for p in b["pages"][1:]]}          # after the players page (#4670)


def total(cost):
    return sum(cost.values())


def test_the_spending_book_has_the_costs_by_group_of_the_player():
    r = replay.Replay(Fake(), data([]))
    r.pay(1, "VILLAGER_MALE", 100_000)
    r.pay(1, "MILITIA", 200_000)
    r.pay(1, "HOUSE", 300_000)
    r.pay(1, "COINAGE", 400_000)
    cmds = r.spending_commands(600_000)
    spent = {"economy": total(train.COSTS["VILLAGER_MALE"]), "military": total(train.COSTS["MILITIA"]),
             "technologies": total(train.COSTS["COINAGE"]), "buildings": total(build.COSTS["HOUSE"])}
    all_ = sum(spent.values())
    share = {g: round(100 * v / all_) for g, v in spent.items()}
    assert book(cmds) == {"title": "Spending", "author": "aoe2mc", "pages": [
        f"■ Player 1 (Britons)\n\nEconomy {spent['economy']} ({share['economy']} %)\n"
        f"Military {spent['military']} ({share['military']} %)\n"
        f"Technologies {spent['technologies']} ({share['technologies']} %)\n"
        f"Buildings {spent['buildings']} ({share['buildings']} %)\nTotal {all_}"]}


def test_a_player_with_no_payment_has_no_page():
    r = replay.Replay(Fake(), data([]))
    r.pay(1, "VILLAGER_MALE", 100_000)
    pages = book(r.spending_commands(600_000))["pages"]
    assert len(pages) == 1 and pages[0].startswith("■ Player 1 (Britons)")


def test_a_payment_after_the_end_is_not_in_the_book():
    r = replay.Replay(Fake(), data([]))
    r.pay(2, "VILLAGER_MALE", 700_000)
    assert r.spending_commands(600_000) == []
