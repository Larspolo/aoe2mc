"""#2541 (epic #2538): in the scenario mode each person gets a written book with the scenario texts (aoe2mc.json
"messages"), as the "Objectives" window of AoE2 DE, and the chat shows the instructions."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import rcon  # noqa: E402
import scenario  # noqa: E402
import scenarios  # noqa: E402
from test_scenario_mode import game  # noqa: E402

import aoe2mc  # noqa: E402

TEXTS = {"instructions": "Hold the <BLUE>bridge.", "objectives": "- Win the game", "hints": ""}


def test_aoe2mc_json_has_the_scenario_texts(tmp_path):
    src = scenarios.tiny(str(tmp_path / "t.aoe2scenario"), TEXTS)
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        messages = json.load(f)["messages"]
    assert messages["instructions"] == "Hold the <BLUE>bridge." and "hints" not in messages   # only the texts


def test_a_long_book_goes_out_in_commands_that_rcon_takes():
    long = {"hints": " ".join(f"Hint number {i} says that the way is long." for i in range(150))}
    cmds = scenario.book("@a", long)
    assert len(cmds) > 1 and all(len(c.encode()) <= rcon.MAX for c in cmds)
    assert cmds[0].startswith("item replace entity @a inventory.26 with written_book[")
    assert all('type:"minecraft:set_written_book_pages",mode:"append"' in c for c in cmds[1:])   # 26.3: "type"
    pages = [scenario.page(p) for p in aoe2mc.book_pages(long)]
    assert sum(c.count(p) for c in cmds for p in set(pages)) == len(pages)          # each page once
    assert scenario.book("@a", {"hints": " "}) == []


def test_a_new_person_gets_the_book_and_the_instructions_once():
    server, g, _ = game({"1": {}, "2": {}})
    g.data["messages"] = TEXTS
    new = {"@a[tag=!aoe_book]"}
    command = server.command

    def answer(cmd):
        if cmd.startswith("execute if entity "):
            server.log.append(cmd)
            return "Test passed, count: 1" if cmd.split()[-1] in new else "Test failed"
        if cmd.startswith("tag "):
            new.clear()
        return command(cmd)
    server.command = answer
    for t in (0.0, 2.0):
        g.clock = lambda t=t: t
        scenario.tick(g)
    books = [c for c in server.log if c.startswith("item replace")]
    chat = [c for c in server.log if c.startswith("tellraw @a[tag=!aoe_book]")]
    assert len(books) == 1 and "Win the game" in books[0]
    assert len(chat) == 1 and '"Hold the bridge."' in chat[0]                      # no AoE2 color tag
    assert "tag @a[tag=!aoe_book] add aoe_book" in server.log


def test_the_selector_of_a_team_keeps_its_team():
    assert scenario.unread("@a[team=p2]") == "@a[team=p2,tag=!aoe_book]"
