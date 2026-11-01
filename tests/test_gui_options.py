"""gui.options and the tab "All options" (#5170): the window offers each option of the command line."""
import aoe2mc
import gui


def test_each_option_of_the_command_line_is_in_the_window():
    shown = {f for f, *_ in gui.options()} | gui.SHOWN
    for a in aoe2mc.parser()._actions:
        assert any(s in shown for s in a.option_strings) or not a.option_strings


def test_kinds_follow_the_parser():
    ap = aoe2mc.parser()
    by = {f: (k, c) for f, k, c, *_ in gui.options(ap)}
    for a in ap._actions:
        flag = next((s for s in a.option_strings if s.startswith("--")), None)
        if flag in by:
            assert by[flag][0] == ("flag" if a.nargs == 0 else "choice" if a.choices else "text")


def test_extra_values_go_into_argv():
    o = {"input": "a.aoe2scenario", "output": "w"}
    flag, value = next((f, c[0]) for f, k, c, *_ in gui.options() if k == "choice")
    box = next(f for f, k, *_ in gui.options() if k == "flag")
    a = gui.argv(o | {"extra": {flag: value, box: True, "--name": "", "--x": False}})
    assert a[2:] == [flag, str(value), box]
    aoe2mc.parser().parse_args(a)
