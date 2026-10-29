"""The precondition of the rule set folder of Antiquity Mode (docs/research/antiquity.md, section 2.3, #3665): run.main
chooses the rule set after it reads the options and the saved settings, so the import of run.py and savegame.py must
load no rule table (a module that calls table.load at import)."""
import glob
import json
import os
import re
import subprocess
import sys

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game")
LOBBY = {"run"}                                      # its table.load at import reads setup.jsonl, a file of both sets


def readers():
    """The modules of game/ that call table.load at import (a line with no indent)."""
    return {os.path.basename(f)[:-3] for f in glob.glob(os.path.join(GAME, "*.py"))
            if re.search(r"^\S.*table\.load\(", open(f, encoding="utf-8").read(), re.M)}


def test_the_options_load_before_the_rules():
    code = f"import sys; sys.path.insert(0, {GAME!r}); import run, savegame, json; print(json.dumps(sorted(sys.modules)))"
    loaded = set(json.loads(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                           check=True).stdout))
    rules = readers() - LOBBY
    assert {"build", "civs", "train"} <= rules                                  # the check finds the readers
    assert not rules & loaded, sorted(rules & loaded)
