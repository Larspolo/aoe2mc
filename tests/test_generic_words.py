"""The generic files of framework/docs/SYSTEM.md do not name the domain of aoe2mc (#1900): the bootstrap copies them into a
new project, and a rename changes only the repository, the owner and the project name."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402

WORDS = re.compile(r"Minecraft|aoe2|AoE2")
ALLOW = {"aoe2mc"}          # the project name: rename() replaces it


def found(path, text):
    """The lines of a generic file with a domain word. The rows of the table in framework/docs/SYSTEM.md say what is specific."""
    return [f"{path}:{i}: {line.strip()[:100]}" for i, line in enumerate(text.splitlines(), 1)
            if WORDS.search(re.sub("|".join(ALLOW), "", line))
            and not (path == "framework/docs/SYSTEM.md" and line.startswith("| `"))]


def test_no_generic_file_names_the_domain():
    bad = []
    for path, kind in bootstrap.rows():
        if kind == "generic":
            try:
                bad += found(path, open(os.path.join(ROOT, path)).read())
            except UnicodeDecodeError:
                pass
    assert bad == []


def test_a_domain_word_fails():
    assert found("tools/x.py", "# start the Minecraft server\nrepo aoe2mc") == ["tools/x.py:1: # start the Minecraft server"]
    assert found("framework/docs/SYSTEM.md", "| `x.sh` | specific | Minecraft jars. |") == []
