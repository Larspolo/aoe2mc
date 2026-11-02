"""The XS interpreter of the game program runs each part of the language and its built-in functions (#5610)."""
import math

import pytest

from game.xs_run import Xs


def run(src, **kw):
    """Run main() of a script and return the lines of xsChatData."""
    lines = []
    x = Xs(src, out=lines.append, **kw)
    x.tick(0)
    return lines


def val(expr, typ="int", pre=""):
    """The value of one expression of type typ."""
    x = Xs(f"{typ} r = 0; void main() {{ {pre} r = {expr}; }}" if typ != "vector" else
           f"vector r = vector(0, 0, 0); void main() {{ {pre} r = {expr}; }}", out=print)
    x.tick(0)
    return x.get("r")


@pytest.mark.parametrize("expr,typ,want", [
    ("7 / 2", "int", 3), ("-7 / 2", "int", -3), ("-7 % 3", "int", -1), ("7.0 / 2", "float", 3.5),
    ("1 + 0.5", "float", 1.5), ("3.9", "int", 3), ("-3.9", "int", -3), ("2147483647 + 1", "int", -2147483648),
    ("2 * 3 + 4", "int", 10), ("2 * (3 + 4)", "int", 14), ("10 - 2 - 3", "int", 5),
    ('"a" + 5', "string", "a5"), ('"a" + true', "string", "atrue"), ('"x" + 1.5', "string", "x1.500000"),
    ("1 < 2 && 2 <= 2", "bool", True), ("1 > 2 || 3 >= 4", "bool", False), ("!(1 == 1)", "bool", False),
    ('"ab" != "ab"', "bool", False), ("-(2)", "int", -2), ("5", "bool", True),
    ("vector(1, 2, 3) + vector(1, 1, 1)", "vector", (2.0, 3.0, 4.0)), ("vector(1, 2, 3) * 2", "vector", (2.0, 4.0, 6.0)),
    ("vector(2, 4, 6) / 2", "vector", (1.0, 2.0, 3.0)), ("-vector(1, 0, 0)", "vector", (-1.0, 0.0, 0.0)),
])
def test_types_and_operators(expr, typ, want):
    got = val(expr, typ)
    assert got == want and type(got) is type(want)


def test_short_circuit_skips_the_right_side():
    assert run('bool f() { xsChatData("called"); return (true); } void main() { if (false && f()) {} if (true || f()) {} }') == []


def test_increment_and_decrement():
    assert val("a++ + a", pre="int a = 1;") == 3              # a++ gives 1, then a is 2
    assert val("--a", pre="int a = 1;") == 0
    assert val("a", pre="int a = 1; a--; ++a; ++a;") == 2


def test_const_cannot_change(capsys):
    x = Xs("const int N = 3; void main() { N = 4; }", out=print)
    x.tick(0)
    assert x.get("N") == 3 and "constant N" in capsys.readouterr().err


def test_static_local_keeps_its_value():
    src = 'int next() { static int n = 0; n++; return (n); } void main() { next(); next(); xsChatData("n %d", next()); }'
    assert run(src) == ["n 3"]


def test_extern_global_is_a_global():
    x = Xs("extern int gold = 5; void main() { gold = gold * 2; }")
    x.tick(0)
    assert x.get("gold") == 10


def test_function_defaults_and_return_type():
    src = """int add(int a = 1, int b = 2) { return (a + b); }
    float half(int v = 3) { return (v / 2.0); }
    void main() { xsChatData("%d", add()); xsChatData("%d", add(5)); xsChatData("%d", add(5, 5)); xsChatData("%d", half()); }"""
    assert run(src) == ["3", "7", "10", "1"]                    # %d shows the int of 1.5


def test_missing_return_gives_the_default():
    x = Xs("string s = \"x\"; string f() { } void main() { s = f(); }")
    x.tick(0)
    assert x.get("s") == ""


def test_recursion():
    x = Xs("int fib(int n = 0) { if (n < 2) { return (n); } return (fib(n - 1) + fib(n - 2)); } int r = 0; "
           "void main() { r = fib(10); }")
    x.tick(0)
    assert x.get("r") == 55


def test_if_else_while_break_continue():
    src = """void main() {
        int i = 0; int s = 0;
        while (true) { i++; if (i > 10) { break; } if (i % 2 == 0) { continue; } s = s + i; }
        if (s == 25) { xsChatData("odd sum"); } else { xsChatData("wrong"); }
    }"""
    assert run(src) == ["odd sum"]


@pytest.mark.parametrize("head,want", [("i = 0; < 3", "0,1,2,"), ("i = 0; <= 2", "0,1,2,"), ("i = 3; > 0", "3,2,1,"),
                                       ("i = 2; >= 0", "2,1,0,")])
def test_for_counts_up_or_down(head, want):
    x = Xs(f'string s = ""; void main() {{ int i = 0; for ({head}) {{ s = s + i + ","; }} }}')
    x.tick(0)
    assert x.get("s") == want


def test_for_break_and_continue():
    x = Xs('string s = ""; void main() { for (i = 0; < 10) { if (i == 1) { continue; } if (i == 4) { break; } '
           's = s + i; } }')
    x.tick(0)
    assert x.get("s") == "023"


def test_switch_takes_one_case_or_default():
    src = """string pick(int v = 0) { string s = "";
        switch (v) { case 1: s = "one"; case 2: { s = "two"; break; } default: s = "other"; }
        return (s); }
        void main() { xsChatData(pick(1)); xsChatData(pick(2)); xsChatData(pick(9)); }"""
    assert run(src) == ["one", "two", "other"]


def test_block_scope():
    x = Xs("int r = 0; void main() { int a = 1; { int a = 2; r = a; } r = r * 10 + a; }")
    x.tick(0)
    assert x.get("r") == 21


def test_include_reads_the_file_once():
    files = {"lib.xs": 'include "lib.xs"; int twice(int v = 0) { return (v * 2); }'}
    assert run('include "lib.xs"; include "lib.xs"; void main() { xsChatData("%d", twice(4)); }',
               load=files.__getitem__) == ["8"]


def test_include_without_loader_warns(capsys):
    assert run('include "lib.xs"; void main() { xsChatData("go"); }') == ["go"]
    assert "lib.xs" in capsys.readouterr().err


def ticks(src, times):
    """The rule calls at the given times: [(time, line)]."""
    got, now = [], [0]
    x = Xs(src, out=lambda t: got.append((now[0], t)))
    for t in times:
        now[0] = t
        x.tick(t)
    return got, x


def test_rule_min_interval_and_run_immediately():
    got, _ = ticks('rule a active minInterval 5 { xsChatData("a"); } rule b active runImmediately minInterval 5 '
                   '{ xsChatData("b"); }', range(12))
    assert got == [(0, "b"), (5, "a"), (5, "b"), (10, "a"), (10, "b")]


def test_rule_default_interval_is_one_second():
    got, _ = ticks('rule a { xsChatData("a"); }', [0, 0.5, 1, 1.5, 2])
    assert [t for t, _ in got] == [1, 2]


def test_rule_max_interval_shorter_than_min():
    got, _ = ticks('rule a active runImmediately minInterval 10 maxInterval 3 { xsChatData("a"); }', range(7))
    assert [t for t, _ in got] == [0, 3, 6]


def test_rule_high_frequency_runs_each_tick():
    got, _ = ticks('rule a highFrequency { xsChatData("a"); }', [0, 0.05, 0.1])
    assert len(got) == 3


def test_rule_priority_order():
    got, _ = ticks('rule low runImmediately priority 1 { xsChatData("low"); } '
                   'rule high runImmediately priority 9 { xsChatData("high"); }', [0])
    assert [t for _, t in got] == ["high", "low"]


def test_inactive_rule_runs_after_enable():
    src = ('rule later inactive runImmediately { xsChatData("later"); xsDisableSelf(); } '
           'rule starter runImmediately priority 5 { xsEnableRule("later"); xsDisableSelf(); }')
    got, x = ticks(src, [0, 1, 2])
    assert got == [(0, "later")] and not x.rules["later"]["on"] and not x.rules["starter"]["on"]


def test_rule_groups():
    src = ('rule a inactive runImmediately group g { xsChatData("a"); } rule b inactive runImmediately group g '
           '{ xsChatData("b"); } rule c runImmediately priority 9 { xsChatData("g " + xsIsRuleGroupEnabled("g")); '
           'xsEnableRuleGroup("g"); xsChatData("on " + xsIsRuleEnabled("a")); xsDisableSelf(); } '
           'rule d minInterval 2 { xsDisableRuleGroup("g"); }')
    got, x = ticks(src, [0, 1, 2, 3])
    assert [t for _, t in got] == ["g false", "on true", "a", "b", "a", "b", "a", "b"]
    assert not x.rules["a"]["on"] and not x.rules["b"]["on"]


def test_set_rule_intervals_and_priority():
    src = ('rule a runImmediately minInterval 1 { xsChatData("a"); xsSetRuleMinIntervalSelf(3); } '
           'rule b inactive { } void main() { xsSetRuleMinInterval("b", 7); xsSetRuleMaxInterval("b", 8); '
           'xsSetRulePriority("b", 4); xsSetRulePrioritySelf(2); xsSetRuleMaxIntervalSelf(9); }')
    got, x = ticks(src, range(7))
    assert [t for t, _ in got] == [0, 3, 6]
    assert (x.rules["b"]["minInterval"], x.rules["b"]["maxInterval"], x.rules["b"]["priority"]) == (7, 8, 4)


def test_main_runs_once_before_the_rules():
    got, _ = ticks('void main() { xsChatData("main"); } rule a runImmediately { xsChatData("a"); }', [0, 1])
    assert [t for _, t in got] == ["main", "a", "a"]


def test_get_time_and_chat_data():
    got, _ = ticks('rule a minInterval 2 { xsChatData("t %d", xsGetTime()); xsChatData("plain"); xsBreakPoint(); }',
                   [0, 2.5])
    assert got == [(2.5, "t 2500"), (2.5, "plain")]


@pytest.mark.parametrize("expr,want", [
    ("abs(-2.5)", 2.5), ("acos(1)", 0.0), ("asin(0)", 0.0), ("atan(0)", 0.0), ("atan2(1, 1)", math.pi / 4),
    ("ceil(1.2)", 2.0), ("cos(0)", 1.0), ("degrees(3.14159265)", 180.0), ("exp(0)", 1.0), ("floor(-1.2)", -2.0),
    ("ln(1)", 0.0), ("log10(100)", 2.0), ("log2(8)", 3.0), ("pow(2, 10)", 1024.0), ("radians(180)", math.pi),
    ("round(2.567, 2)", 2.57), ("round(2.5)", 2.0), ("sin(0)", 0.0), ("sqrt(16)", 4.0), ("tan(0)", 0.0),
    ("xsCeilToInt(1.1)", 2.0), ("dist(vector(0, 0, 0), vector(3, 4, 0))", 5.0),
    ("xsVectorGetX(vector(1, 2, 3))", 1.0), ("xsVectorGetY(vector(1, 2, 3))", 2.0),
    ("xsVectorGetZ(vector(1, 2, 3))", 3.0), ("xsVectorLength(vector(3, 0, 4))", 5.0),
])
def test_math_functions(expr, want):
    assert val(expr, "float") == pytest.approx(want, abs=1e-6)


@pytest.mark.parametrize("expr,want", [
    ("xsVectorSet(1, 2, 3)", (1.0, 2.0, 3.0)), ("xsVectorSetX(vector(1, 2, 3), 9)", (9.0, 2.0, 3.0)),
    ("xsVectorSetY(vector(1, 2, 3), 9)", (1.0, 9.0, 3.0)), ("xsVectorSetZ(vector(1, 2, 3), 9)", (1.0, 2.0, 9.0)),
    ("xsVectorNormalize(vector(0, 3, 4))", (0.0, 0.6, 0.8)), ("xsVectorNormalize(vector(0, 0, 0))", (0.0, 0.0, 0.0)),
])
def test_vector_functions(expr, want):
    assert val(expr, "vector") == pytest.approx(want)


def test_unknown_function_warns_once_and_goes_on(capsys):
    assert run('void main() { xsNoSuch(1); xsNoSuch(2); int v = nothing; xsChatData("next"); }') == ["next"]
    err = capsys.readouterr().err.splitlines()
    assert sum("xsNoSuch" in e for e in err) == 1 and sum("nothing" in e for e in err) == 1


def test_host_function():
    assert run('void main() { xsChatData("%d", xsGetGameTime()); }', host={"xsGetGameTime": lambda: 42}) == ["42"]


def test_endless_loop_stops_and_other_rules_run(capsys):
    got, _ = ticks('rule spin runImmediately priority 9 { while (true) { } } rule ok runImmediately { xsChatData("ok"); }',
                   [0, 1])
    assert [t for _, t in got] == ["ok", "ok"]
    err = capsys.readouterr().err
    assert "step limit" in err and "spin" in err


def test_division_by_zero_stops_only_its_rule(capsys):
    got, _ = ticks('rule bad runImmediately priority 9 { int z = 0; int v = 1 / z; xsChatData("no"); } '
                   'rule ok runImmediately { xsChatData("ok"); }', [0])
    assert [t for _, t in got] == ["ok"]
    assert "division by zero" in capsys.readouterr().err
