"""framework/tools/unconflict.py solves the hunk of a ticket series that adds keys before the first key of a table
whose first entry is on its opening line, `return {"KEY": ...` (the XS functions of game/xs_host.py, #5860)."""
import os
import sys

from test_unconflict import git, tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import unconflict  # noqa: E402

BASE = '''def host(g):
    def size():
        return 1

    return {"xsGetGameTime": lambda: 0,
            "xsGetMapWidth": size,
            "xsTriggerVariable": size}
'''


def merge(tmp_path, ours, theirs, base=BASE):
    """A repository in a merge of `theirs` into `ours` (both changes of base in t.py) that git cannot solve."""
    d, f = str(tmp_path), tmp_path / "t.py"
    git(d, "init", "-q", "-b", "main")
    f.write_text(base)
    git(d, "add", "t.py")
    git(d, "commit", "-qm", "base")
    git(d, "checkout", "-qb", "side")
    f.write_text(theirs)
    git(d, "commit", "-qam", "theirs")
    git(d, "checkout", "-q", "main")
    f.write_text(ours)
    git(d, "commit", "-qam", "ours")
    assert git(d, "merge", "-q", "--no-edit", "side").returncode != 0
    assert '||||||| ' in f.read_text() and '    return {"xsGetGameTime"' in f.read_text().split("|||||||")[1]
    return d


def keys(text):
    """The keys of the table of host(), in the order of the file."""
    scope = {}
    exec(compile(text, "t.py", "exec"), scope)
    return list(scope["host"](None))


def test_defs_and_keys_before_and_after_the_first_key(tmp_path):
    # PR #5850 (bc587df): both sides add functions, a key before the first key and keys after it.
    ours = BASE.replace('    return {"xsGetGameTime": lambda: 0,\n',
                        '    def in_game(player):\n        return True\n\n'
                        '    return {"xsGetContextPlayer": lambda: 1,\n'
                        '            "xsGetGameTime": lambda: 0,\n'
                        '            "xsGetMapName": in_game,\n')
    theirs = BASE.replace('    return {"xsGetGameTime": lambda: 0,\n',
                          '    def object_class(player=-1, unit=-1):\n        return 0\n\n'
                          '    return {"xsGetDamageClassName": lambda: "",\n'
                          '            "xsGetGameTime": lambda: 0,\n'
                          '            "xsGetMapHeight": object_class,\n')
    d = merge(tmp_path, ours, theirs)
    r = tool(d)
    assert r.returncode == 0, r.stdout
    text = (tmp_path / "t.py").read_text()
    assert "def in_game(player)" in text and "def object_class(" in text
    assert keys(text) == sorted(keys(text)) == sorted(set(keys(ours)) | set(keys(theirs)))
    assert '    return {"xsGetContextPlayer": lambda: 1,\n            "xsGetDamageClassName"' in text


def test_a_key_before_the_first_key_on_both_sides():
    # PR #5855 (a39c8a8): the hunk as git gives it, with the base of the hunk.
    text = ('def host(g):\n'
            '<<<<<<< HEAD\n'
            '    return {"xsEffectAmount": g,\n'
            '            "xsGetDamageClassName": g,\n'
            '||||||| e3397d4\n'
            '    return {"xsGetDamageClassName": g,\n'
            '=======\n'
            '    return {"xsDoesUnitExist": g,\n'
            '            "xsGetDamageClassName": g,\n'
            '>>>>>>> 92e0306\n'
            '            "xsTriggerVariable": g}\n')
    solved, why = unconflict.solve(text)
    assert why == "" and unconflict.check("t.py", solved) == ""
    assert solved == ('def host(g):\n'
                      '    return {"xsDoesUnitExist": g,\n'
                      '            "xsEffectAmount": g,\n'
                      '            "xsGetDamageClassName": g,\n'
                      '            "xsTriggerVariable": g}\n')


def test_a_changed_first_entry_stays_a_conflict(tmp_path):
    ours = BASE.replace('    return {"xsGetGameTime": lambda: 0,\n',
                        '    return {"xsGetContextPlayer": lambda: 1,\n            "xsGetGameTime": lambda: 2,\n')
    theirs = BASE.replace('    return {"xsGetGameTime": lambda: 0,\n',
                          '    return {"xsGetDamageClassName": lambda: "",\n            "xsGetGameTime": lambda: 0,\n')
    d = merge(tmp_path, ours, theirs)
    r = tool(d)
    assert r.returncode == 1 and "both sides change the same lines" in r.stdout
    assert "<<<<<<<" in (tmp_path / "t.py").read_text()          # not written


def test_a_nested_function_that_hides_a_module_function_stays_a_conflict(tmp_path):
    # PR #5853 (52645af): one side adds a module civ_name that host() calls, the other a nested civ_name in host().
    ours = 'def civ_name(civ):\n    return "Britons"\n\n\n' + BASE.replace(
        '    return {"xsGetGameTime": lambda: 0,\n',
        '    return {"xsGetCivName": lambda civ: civ_name(civ),\n            "xsGetGameTime": lambda: 0,\n')
    theirs = BASE.replace('    return {"xsGetGameTime": lambda: 0,\n',
                          '    def civ_name(uid):\n        return ""\n\n'
                          '    return {"xsGetDamageClassName": lambda: "",\n            "xsGetGameTime": lambda: 0,\n'
                          '            "xsGetUnitCivName": civ_name,\n')
    d = merge(tmp_path, ours, theirs)
    r = tool(d)
    assert r.returncode == 1 and "hides the module function civ_name" in r.stdout
    assert "<<<<<<<" in (tmp_path / "t.py").read_text()
