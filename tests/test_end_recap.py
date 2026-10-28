"""#2660: at the end of a game (cheats.over) each person gets the recap book in hotbar slot 0, and the items that give
orders leave the hotbar, as the end screen of AoE2 DE. A bot gets no book."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import cheats  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def ended():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    bot.share = g                                                      # a bot: bot.Bot sets it
    g.techs.add("LOOM")
    train.research(g, {"name": "FEUDAL_AGE", "player": "@a"})
    g.losses = {"u1": "MILITIA"}
    start = len(server.log)
    cheats.over(g, lambda n: n == 1)
    return server.log[start:], g, bot


def test_the_person_gets_the_recap_book_in_slot_0():
    log, g, _ = ended()
    books = [c for c in log if "written_book" in c or "set_written_book_pages" in c]
    assert books[0].startswith('item replace entity @a[team=p1] hotbar.0 with written_book[written_book_content={title:"Recap"')
    text = "".join(books)
    for part in ("Player 1", "Player 2", "Victory", "Defeat", "score", "Military", "Economy", "Technology", "Society",
                 "Game time", "Loom", "Feudal Age", "1 lost", "Buildings"):
        assert part in text, part


def test_the_order_items_leave_the_hotbar():
    log, _, _ = ended()
    assert "clear @a[team=p1] minecraft:carrot_on_a_stick" in log      # wand, groups, Go to, Game menu
    assert "clear @a[team=p1] minecraft:warped_fungus_on_a_stick" in log   # the selection wand (vanilla)
    first = log.index("clear @a[team=p1] minecraft:carrot_on_a_stick")
    assert all(not c.startswith("item replace entity @a[team=p1] hotbar.0") for c in log[:first])   # the book after


def test_a_bot_gets_no_book():
    log, _, _ = ended()
    assert not any("team=p2" in c and ("written_book" in c or c.startswith("clear")) for c in log)


def test_the_game_time_of_an_age_is_kept():
    _, g, _ = ended()
    assert set(g.age_times) == {"FEUDAL_AGE"} and g.age_times["FEUDAL_AGE"] >= 0
    assert recap.mmss(125.7) == "2:05"


def test_a_player_without_a_gather_has_its_result():
    server, g, _ = game({"0": {}, "1": {"civ": "BRITONS"}, "3": {"civ": "RANDOM"}, "4": {}})
    g.bots, g.data["objects"] = [], [dict(kind="unit", name="KNIGHT", player=3)]   # player 4: an empty slot
    text = dict(recap.parts(g, lambda n: n == 1))["Recap"]
    assert "Player 1 (Britons): Victory, score" in text and "Player 3: Defeat\n" in text + "\n"
    assert "Player 4" not in text
