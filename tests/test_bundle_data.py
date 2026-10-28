"""#2839: the app bundle keeps the converter data (data/*.jsonl, units.py) and the game data (game/data/*.jsonl,
table.load) in two folders: both have train.jsonl and units.jsonl, and one replaced the other (KeyError in civs.py)."""
import os
import re

from game import table

ROOT = os.path.join(os.path.dirname(__file__), "..")


def folders():
    """{source folder: bundle folder} of the *.jsonl lines of packaging/aoe2mc.spec."""
    spec = open(os.path.join(ROOT, "packaging", "aoe2mc.spec"), encoding="utf-8").read()
    found = re.findall(r'\(os\.path\.join\((ROOT|GAME), "data", "\*\.jsonl"\), "(\w+)"\)', spec)
    return {{"ROOT": "data", "GAME": os.path.join("game", "data")}[k]: v for k, v in found}


def test_the_two_data_sets_have_their_own_bundle_folders():
    f = folders()
    assert f == {"data": "data", os.path.join("game", "data"): table.FROZEN}
    same = set(os.listdir(os.path.join(ROOT, "data"))) & set(os.listdir(os.path.join(ROOT, "game", "data")))
    assert "train.jsonl" in same                                       # the reason for two folders


def test_a_frozen_game_program_reads_its_own_folder():
    assert table.folder(frozen=False) == table.DIR and table.DIR.endswith(os.path.join("game", "data"))
    assert table.folder(frozen=True) == os.path.join(os.path.dirname(table.DIR), table.FROZEN)   # next to the modules
