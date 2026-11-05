"""The file functions of an XS script (game/xs_host.py `files`, #5845): a script writes a file of the world, a second
script reads it again."""
from types import SimpleNamespace as NS

from game import xs_host
from game.xs_run import Xs
from tests.test_xs_host import side


def world(tmp_path):
    g = side()
    g.game = NS(world=str(tmp_path))
    g.data["xs_script"] = ["maps/keep.xs", ""]
    return g


def run(g, body, globals_=""):
    x = Xs(f"{globals_} void main() {{ {body} }}", out=print, host=xs_host.host(g))
    x.tick(0)
    return x


def test_write_then_read_in_a_second_script(tmp_path):
    g = world(tmp_path)
    run(g, 'xsCreateFile(); xsWriteInt(42); xsWriteFloat(1.5); xsWriteString("hello"); '
           'xsWriteVector(vector(1, 2, 3)); xsCloseFile();')
    assert (tmp_path / "xs" / "keep.xsdat").stat().st_size == 4 + 4 + 4 + 5 + 12
    x = run(g, 'ok = xsOpenFile("keep"); size = xsGetFileSize(); i = xsReadInt(); f = xsReadFloat(); '
               's = xsReadString(); v = xsReadVector(); at = xsGetFilePosition(); xsCloseFile();',
            'bool ok = false; int size = 0; int i = 0; float f = 0.0; string s = ""; vector v = vector(0, 0, 0); '
            'int at = 0;')
    assert x.get("ok") and x.get("size") == 29 and x.get("at") == 29
    assert (x.get("i"), x.get("f"), x.get("s"), x.get("v")) == (42, 1.5, "hello", (1.0, 2.0, 3.0))


def test_append_and_positions(tmp_path):
    g = world(tmp_path)
    run(g, 'xsCreateFile(); xsWriteInt(1); xsWriteString("ab"); xsCloseFile(); '
           'xsCreateFile(true); xsWriteInt(3); xsCloseFile();')
    x = run(g, 'xsOpenFile(); xsOffsetFilePosition(0, true); xsOffsetFilePosition(2, true); a = xsReadInt(); '
               'xsSetFilePosition(0); b = xsReadInt(); back = xsOffsetFilePosition(0, false); xsCloseFile();',
            'int a = 0; int b = 0; bool back = true;')
    assert (x.get("a"), x.get("b"), x.get("back")) == (3, 1, False)


def test_a_bad_name_or_no_file_fails_and_warns(tmp_path, capsys):
    g = world(tmp_path)
    x = run(g, 'a = xsOpenFile("../up"); b = xsOpenFile("missing"); i = xsReadInt(); w = xsWriteInt(5);',
            'bool a = true; bool b = true; int i = 0; bool w = true;')
    assert (x.get("a"), x.get("b"), x.get("i"), x.get("w")) == (False, False, -1, False)
    assert capsys.readouterr().err.count("unknown file ../up") == 1
    assert not (tmp_path.parent / "up.xsdat").exists()
