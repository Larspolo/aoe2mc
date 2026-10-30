"""A new project starts from framework/template (#4196): the bootstrap writes the template files and the framework
files, and no file of this project."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402
from test_generic_words import found  # noqa: E402


def test_the_bootstrap_writes_the_template_and_the_framework(tmp_path):
    bootstrap.bootstrap(str(tmp_path), "me/demo")
    got = {os.path.relpath(os.path.join(d, f), tmp_path) for d, _, fs in os.walk(tmp_path) for f in fs}
    tpl = set(bootstrap.template())
    generic = {p for p, k in bootstrap.rows() if k == "generic"}
    assert tpl and got == tpl | generic
    bad = [b for p in got for b in found(p, open(tmp_path / p, errors="replace").read())]
    assert bad == []
    assert not [p for p in tpl if "{name}" in open(tmp_path / p, errors="replace").read()]


def test_the_new_project_guide_names_the_template_and_system_links_it():
    text = open(os.path.join(ROOT, "framework/docs/NEW_PROJECT.md")).read()
    assert "framework/template/" in text and "bootstrap.py" in text
    assert "framework/docs/NEW_PROJECT.md" in open(os.path.join(ROOT, "framework/docs/SYSTEM.md")).read()
