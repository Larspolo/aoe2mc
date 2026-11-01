"""One command of `aoe batch` that throws must not drop the rest of the batch (#5443), and the append command of a
long replay book names its item modifier with the key `type` of 26.3 (docs/minecraft-versions.md)."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import replay  # noqa: E402

PLUGIN = os.path.join(ROOT, "game", "plugin", "src", "main", "java", "aoe2mc", "AoePlugin.java")


def test_the_batch_loop_catches_the_exception_of_one_command():
    src = open(PLUGIN, encoding="utf-8").read()
    loop = re.search(r'args\[0\]\.equals\("batch"\).*?sendMessage\("Batch: ', src, re.S).group(0)
    body = loop[loop.index("for (int i = 1"):]
    assert body.index("try {") < body.index("dispatchCommand") < body.index("catch (RuntimeException")


def test_the_append_command_of_a_long_book_uses_the_key_type():
    cmds = replay.slot_book("hotbar.6", "Economy", [replay.text("x" * 200 + f" {i}") for i in range(80)])
    assert len(cmds) > 1
    assert all('{type:"minecraft:set_written_book_pages",mode:"append"' in c for c in cmds[1:])
