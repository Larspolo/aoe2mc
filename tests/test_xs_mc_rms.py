"""#5696 (epic #5119): the #includeXS file of a random map script (--xs FILE) compiles to the xs/ datapack functions,
as the XS file of a scenario (#5689)."""
import os

from test_rmap_includexs import world

XS = 'int n = 0;\nvoid main() { n = n + 1; }\n'


def functions(tmp_path, xs):
    world(tmp_path, xs=xs)
    folder = next(p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("W"))
    root = folder / "datapacks"
    return {os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            for d, _, fs in os.walk(root) for f in fs if "/function/xs/" in os.path.join(d, f).replace(os.sep, "/")}


def test_the_datapack_has_the_xs_functions(tmp_path):
    fns = functions(tmp_path, XS)
    assert any(f.endswith("xs/tick.mcfunction") for f in fns), fns
    assert len(fns) > 1


def test_no_xs_file_gives_no_xs_functions(tmp_path):
    assert not functions(tmp_path, None)
