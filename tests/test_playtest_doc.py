"""Each command of docs/PLAYTEST.md uses only real options and kinds (#3326)."""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "docs", "PLAYTEST.md")
PROGRAMS = {"game/run.py": "game/run.py", "aoe2mc.py": "aoe2mc.py", "tools/scenarios.py": "tools/scenarios.py"}


def commands():
    """(program, arguments) of each `python3 PROGRAM ...` line of the page."""
    return [(m.group(1), m.group(2).split()) for line in open(PAGE).read().splitlines()
            if (m := re.match(r"\s+python3 (\S+\.py)(.*)$", line)) and m.group(1) in PROGRAMS]


def helptext(program):
    return subprocess.run([sys.executable, os.path.join(ROOT, program), "--help"], capture_output=True, text=True,
                          cwd=ROOT).stdout


def test_page_has_the_five_parts_and_readme_links_it():
    text = open(PAGE).read()
    assert re.findall(r"^## (\d)\.", text, re.M) == list("12345")
    assert "docs/PLAYTEST.md" in open(os.path.join(ROOT, "README.md")).read()


def test_each_option_of_the_page_is_an_option_of_its_program():
    found = commands()
    assert {p for p, _ in found} == set(PROGRAMS)
    helps = {p: helptext(p) for p in PROGRAMS}
    options = [o for o in re.findall(r"`(--[a-z-]+)", open(PAGE).read())]
    for program, args in found:
        for a in args:
            if a.startswith("--"):
                assert re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", helps[program]), f"{program} has no {a}"
    for o in options:                                  # an option in the text: of the game program
        assert re.search(rf"(?<![\w-]){re.escape(o)}(?![\w-])", helps["game/run.py"]), f"game/run.py has no {o}"


def test_the_scenario_kind_of_the_page_exists():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import scenarios
    for program, args in commands():
        if program == "tools/scenarios.py":
            assert args[0] in ["gallery", *scenarios.MAKERS]
