"""The trigger ID of the autopilot task is in agent.toml, not in a generic file (#1898): a bootstrap copies the
generic files, and a pacer of a new project must not start the runs of this one."""
import os
import re
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402

ID = re.compile(r"trig_[0-9A-Za-z]{8,}")


def test_no_generic_file_has_a_trigger_id():
    rows = bootstrap.table(open(bootstrap.SYSTEM).read())
    found = [p for p, kind in rows if kind == "generic" and os.path.isfile(os.path.join(ROOT, p))
             and ID.search(open(os.path.join(ROOT, p), errors="replace").read())]
    assert found == []


def test_a_new_project_gets_an_empty_trigger():
    new = tomllib.loads(bootstrap.CONFIG_TOML.format(repo="me/demo", owner="me", branch="main"))
    assert new["pacing"]["trigger"] == ""
