"""The array functions of an XS script (game/xs_run.py, #5838): create, get, set, resize, size, dump and the save."""
import json

from game import savegame
from game.xs_run import Xs


def run(body, typ="int", out=None):
    x = Xs(f"{typ} r; void main() {{ {body} }}", out=out or print)
    x.tick(0)
    return x


def test_each_type_keeps_its_values():
    for t, default, v in (("Bool", "false", "true"), ("Float", "-1.0", "2.5"), ("Int", "-1", "7"),
                          ("String", '""', '"a"'), ("Vector", "vector(-1, -1, -1)", "vector(1, 2, 3)")):
        typ = t.lower()
        x = run(f"int a = xsArrayCreate{t}(3, {default}, \"n\"); xsArraySet{t}(a, 1, {v}); r = xsArrayGet{t}(a, 1);",
                typ)
        y = run(f"int a = xsArrayCreate{t}(3, {v}); r = xsArrayGet{t}(a, 2);", typ)
        assert x.get("r") == y.get("r") != run(f"r = {default};", typ).get("r"), t


def test_default_value_size_and_resize():
    assert run("int a = xsArrayCreateInt(4); r = xsArrayGetInt(a, 3);").get("r") == -1
    assert run("int a = xsArrayCreateFloat(2); r = xsArrayGetFloat(a, 0);", "float").get("r") == -1.0
    assert run("int a = xsArrayCreateInt(4, 5); xsArrayResizeInt(a, 6); r = xsArrayGetSize(a);").get("r") == 6
    for t in ("Bool", "Float", "String", "Vector"):
        assert run(f"int a = xsArrayCreate{t}(4); xsArrayResize{t}(a, 1); r = xsArrayGetSize(a);").get("r") == 1
    x = run("int a = xsArrayCreateInt(1, 5); xsArrayResizeInt(a, 3); xsArraySetInt(a, 2, 9); "
            "r = xsArrayGetInt(a, 0) + xsArrayGetInt(a, 1) + xsArrayGetInt(a, 2);")
    assert x.get("r") == 14


def test_bad_index_or_id_warns_once_and_the_script_goes_on(capsys):
    x = run("int a = xsArrayCreateInt(2, 4); r = xsArrayGetInt(a, 5) + xsArrayGetInt(a, 5) + xsArrayGetInt(9, 0); "
            "bool ok = xsArraySetInt(a, -1, 3); r = r + xsArrayGetSize(9) + xsArrayGetInt(a, 1);")
    assert x.get("r") == 0 + 0 + 0 - 1 + 4
    err = capsys.readouterr().err
    assert err.count("index of array 0") == 2 and err.count("unknown int array 9") == 1


def test_dump_shows_each_array():
    lines = []
    run('int a = xsArrayCreateInt(2, 3, "x"); int b = xsArrayCreateString(1, "s"); xsDumpArrays();', out=lines.append)
    assert len(lines) == 2 and "3, 3" in lines[0] and "x" in lines[0] and "s" in lines[1]


def test_the_save_keeps_the_arrays():
    src = "int a = -1; void main() { a = xsArrayCreateVector(2, vector(1, 2, 3)); xsArraySetVector(a, 1, vector(4, 5, 6)); }"
    x = Xs(src, out=print)
    x.tick(0)
    d = json.loads(json.dumps({"xs": savegame.xs_state(x)}))
    y = Xs(src, out=print)
    savegame.xs_again(type("G", (), {"xs": y})(), d)
    assert y.arrays == x.arrays and y.arrays[0][2][1] == (4.0, 5.0, 6.0)
