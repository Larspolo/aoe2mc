"""The XS parser reads each construct of the language into nodes (#5121)."""
import pytest

from xs import XsError, parse


def body(src):
    return parse("void main() {" + src + "}")[0][4][1]


def test_comments_and_var_decls():
    nodes = parse('// a\n/* b\n c */ const int N = 3; static float f = 1.5; extern string s = "a\\"b"; bool b;')
    assert nodes == [("var", "int", "N", ("num", 3), frozenset({"const"})),
                     ("var", "float", "f", ("num", 1.5), frozenset({"static"})),
                     ("var", "string", "s", ("str", 'a"b'), frozenset({"extern"})),
                     ("var", "bool", "b", None, frozenset())]


def test_function_with_defaults_and_return():
    (fn,) = parse("int add(int a = 1, vector v = vector(0, 0, 0)) { return (a + 2); }")
    assert fn[:4] == ("func", "int", "add", [("int", "a", ("num", 1)),
                      ("vector", "v", ("call", "vector", [("num", 0)] * 3))])
    assert fn[4] == ("block", [("return", ("bin", "+", ("name", "a"), ("num", 2)))])


def test_if_else_and_while():
    assert body("if (a) b(); else { c(); } while (x < 3) x++;") == [
        ("if", ("name", "a"), ("expr", ("call", "b", [])), ("block", [("expr", ("call", "c", []))])),
        ("while", ("bin", "<", ("name", "x"), ("num", 3)), ("expr", ("post", "++", ("name", "x"))))]


def test_xs_for_form():
    assert body("for (i = 0; < 10) { continue; }") == [
        ("for", "i", ("num", 0), "<", ("num", 10), ("block", [("continue",)]))]


def test_switch_case_default_break():
    assert body("switch (n) { case 1: { x = 2; break; } default: x--; }") == [
        ("switch", ("name", "n"), [(("num", 1), [("block", [("expr", ("assign", "x", ("num", 2))), ("break",)])]),
                                   (None, [("expr", ("post", "--", ("name", "x")))])])]


def test_operator_precedence():
    (s,) = body("x = !a || b && c == 1 + 2 * 3 % 4 - -5 / 6 != (d >= e);")
    e = s[1][2]
    assert e[:2] == ("bin", "||") and e[2] == ("unary", "!", ("name", "a"))
    assert e[3][:2] == ("bin", "&&") and e[3][3][:2] == ("bin", "!=")
    assert body("y = a <= b > c;")[0][1][2] == ("bin", ">", ("bin", "<=", ("name", "a"), ("name", "b")), ("name", "c"))


def test_include_and_rule():
    nodes = parse('include "lib.xs";\nrule tick active minInterval 1 maxInterval 5 highFrequency runImmediately '
                  'priority 100 group main { xsDisableSelf(); }')
    assert nodes == [("include", "lib.xs"),
                     ("rule", "tick", {"active": True, "minInterval": 1, "maxInterval": 5, "highFrequency": True,
                                       "runImmediately": True, "priority": 100, "group": "main"},
                      ("block", [("expr", ("call", "xsDisableSelf", []))]))]


@pytest.mark.parametrize("src, line", [("int a = ;", 1), ("void f() {\n  x = 1\n}", 3),
                                       ("void f() {\n\n for (i = 0; 10) {} }", 3), ("int a = 1 @;", 1),
                                       ("rule r bogus {}", 1)])
def test_syntax_error_has_line(src, line):
    with pytest.raises(XsError) as err:
        parse(src, "t.xs")
    assert err.value.line == line and "t.xs:" in str(err.value)
