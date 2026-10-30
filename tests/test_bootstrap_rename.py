"""framework/tools/bootstrap.py: rename() never replaces a new value again (#953)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import bootstrap  # noqa: E402


def test_a_new_name_that_contains_the_old_one():
    assert bootstrap.rename("Larspolo/aoe2mc and aoe2mc", "Larspolo/aoe2mc-second", "aoe2mc-second", "Larspolo") == \
        "Larspolo/aoe2mc-second and aoe2mc-second"


def test_a_new_owner_and_name():
    assert bootstrap.rename("`Larspolo/aoe2mc`, owner Larspolo, aoe2mc.py", "me/tool", "tool", "me") == \
        "`me/tool`, owner me, tool.py"
