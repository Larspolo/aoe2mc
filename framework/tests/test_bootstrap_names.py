"""A bootstrap with a hyphenated project name keeps the Python modules importable (#4795)."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import bootstrap  # noqa: E402

# a module use in code: `import my-app` or a call `my-app.convert(`; file names in strings (`"aoe2mc.py"`) are no use
MODULE_USE = re.compile(r"^\s*import my-app\b|(?<![\w`'\"./-])my-app\.\w+\(", re.M)


def test_no_copied_python_file_uses_the_hyphenated_name_as_a_module(tmp_path):
    bootstrap.main([str(tmp_path), "--repo", "someone/my-app"])
    pys = [os.path.join(d, f) for d, _, fs in os.walk(tmp_path) for f in fs if f.endswith(".py")]
    assert pys
    for path in pys:
        assert not MODULE_USE.search(open(path).read()), path
