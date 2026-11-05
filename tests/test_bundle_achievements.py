"""The app bundle found no data/achievements.jsonl: achievements.py read it one folder up, but in a bundle the modules
of game/ are next to the folder data (packaging/aoe2mc.spec), so aoe2mc-game stopped at the import of savegame."""
import os

from game import achievements


def test_a_source_checkout_reads_the_converter_data():
    assert achievements.path(frozen=False) == achievements.PATH and os.path.isfile(achievements.PATH)


def test_a_frozen_game_program_reads_data_next_to_its_modules():
    here = os.path.dirname(os.path.abspath(achievements.__file__))
    assert achievements.path(frozen=True) == os.path.join(here, "data", "achievements.jsonl")
