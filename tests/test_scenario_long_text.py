"""#2969: a long or non-ASCII scenario text goes out in commands that RCON takes (rcon.MAX bytes each), for the book
and for the chat line of the instructions."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import rcon  # noqa: E402
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

import aoe2mc  # noqa: E402

SEL = "@a[tag=!aoe_book]"


def sent(text):
    """The commands of one check of scenario.tick with the instructions text. The fake server raises above rcon.MAX
    bytes, as rcon.Rcon.command does."""
    server, g, _ = game({"1": {}, "2": {}})
    g.data["messages"] = {"instructions": text}
    new = {SEL}
    command = server.command

    def answer(cmd):
        if len(cmd.encode()) > rcon.MAX:
            raise rcon.RconError(f"RCON command of {len(cmd.encode())} bytes, the limit is {rcon.MAX}: {cmd[:80]}")
        if cmd.startswith("execute if entity "):
            return "Test passed, count: 1" if cmd.split()[-1] in new else "Test failed"
        if cmd.startswith("tag "):
            new.clear()
        return command(cmd)
    server.command = answer
    g.clock = lambda: 0.0
    scenario.tick(g)
    return [c for c in server.log if c.startswith(f"tellraw {SEL} ")]


def shown(cmds):
    """The text of each chat command, joined in their order."""
    return "".join(json.loads(c.split(" ", 2)[2])["text"] for c in cmds)


def test_long_english_instructions_go_out_in_commands_that_rcon_takes():
    text = " ".join(f"Step {i} holds the bridge." for i in range(90))
    cmds = sent(text)
    assert len(cmds) > 1 and all(len(c.encode()) <= rcon.MAX for c in cmds)
    assert shown(cmds) == text


def test_long_cyrillic_instructions_go_out_in_commands_that_rcon_takes():
    text = " ".join(f"Шаг {i}: удерживайте мост." for i in range(60))
    cmds = sent(text)
    assert len(cmds) > 1 and all(len(c.encode()) <= rcon.MAX for c in cmds)
    assert shown(cmds) == text


def test_long_chinese_instructions_with_no_spaces_go_out_in_commands_that_rcon_takes():
    text = "".join(chr(0x4E00 + i) for i in range(600))
    cmds = sent(text)
    assert len(cmds) > 1 and all(len(c.encode()) <= rcon.MAX for c in cmds)
    assert shown(cmds) == text


def test_a_chinese_history_chapter_goes_out_in_commands_that_rcon_takes():
    history = "".join(chr(0x4E00 + i) for i in range(960))
    cmds = scenario.book("@a", {"history": history})
    pages = [scenario.page(p) for p in aoe2mc.book_pages({"history": history})]
    assert all(len(c.encode()) <= rcon.MAX for c in cmds)
    assert sum(c.count(p) for c in cmds for p in pages) == len(pages)              # each page once
