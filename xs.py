"""A parser for the XS scripts of AoE2 DE: text -> syntax tree (#5121, epic #5119).

Each node is a tuple with its kind first, as ('call', 'xsChatData', [args]). No file is read here: an
`include` stays a node. The interpreter or compiler of #5120 walks the tree.
"""
import re

TYPES = {"int", "float", "bool", "string", "vector", "void"}
TOKEN = re.compile(r"""(?P<ws>[ \t\r\n]+|//[^\n]*|/\*.*?\*/)|(?P<num>\d+\.\d*|\.\d+|\d+)|(?P<str>"(?:\\.|[^"\\\n])*")
    |(?P<name>[A-Za-z_]\w*)|(?P<op>\+\+|--|==|!=|<=|>=|&&|\|\||[-+*/%<>=!(){};,:])""", re.S | re.X)
BINARY = [("||",), ("&&",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/", "%")]
RULE_FLAGS = {"active", "inactive", "highFrequency", "runImmediately"}
RULE_VALUES = {"minInterval", "maxInterval", "priority", "group"}


class XsError(SyntaxError):
    def __init__(self, msg, line, col, path=None):
        super().__init__(f"{path or '<xs>'}:{line}:{col}: {msg}")
        self.line, self.col, self.path = line, col, path


def tokenize(text, path=None):
    """Yield (kind, value, line, col); kind 'end' at the end."""
    pos, line, start = 0, 1, 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise XsError(f"bad character {text[pos]!r}", line, pos - start + 1, path)
        if m.lastgroup != "ws":
            yield m.lastgroup, m.group(), line, pos - start + 1
        nl = text.count("\n", pos, m.end())
        if nl:
            line, start = line + nl, text.rindex("\n", pos, m.end()) + 1
        pos = m.end()
    yield "end", "", line, pos - start + 1


class Parser:
    def __init__(self, text, path=None):
        self.toks, self.i, self.path = list(tokenize(text, path)), 0, path

    def peek(self, k=0):
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def error(self, msg):
        _, v, line, col = self.peek()
        raise XsError(f"{msg}, got {v or 'end of file'!r}", line, col, self.path)

    def accept(self, value):
        if self.peek()[1] == value and self.peek()[0] in ("op", "name"):
            self.i += 1
            return True
        return False

    def expect(self, value):
        if not self.accept(value):
            self.error(f"expected {value!r}")

    def take(self, kind):
        if self.peek()[0] != kind:
            self.error(f"expected {kind}")
        self.i += 1
        return self.toks[self.i - 1][1]

    def program(self):
        nodes = []
        while self.peek()[0] != "end":
            nodes.append(self.top())
        return nodes

    def top(self):
        if self.accept("include"):
            node = ("include", self.string())
            self.expect(";")
            return node
        if self.accept("rule"):
            return self.rule()
        return self.decl(top=True)

    def string(self):
        return bytes(self.take("str")[1:-1], "utf-8").decode("unicode_escape")

    def rule(self):
        name, opts = self.take("name"), {}
        while self.peek()[1] != "{":
            word = self.take("name")
            if word in RULE_FLAGS:
                opts[word] = True
            elif word in RULE_VALUES:
                opts[word] = self.take("name") if word == "group" else self.number()
            else:
                self.i -= 1
                self.error("expected a rule option")
        return ("rule", name, opts, self.block())

    def number(self):
        neg = self.accept("-")
        v = self.take("num")
        v = float(v) if "." in v else int(v)
        return -v if neg else v

    def is_decl(self):
        k = 0
        while self.peek(k)[1] in ("extern", "const", "static"):
            k += 1
        return self.peek(k)[0] == "name" and self.peek(k)[1] in TYPES and self.peek(k + 1)[0] == "name"

    def decl(self, top=False):
        mods = set()
        while self.peek()[1] in ("extern", "const", "static"):
            mods.add(self.take("name"))
        if not self.is_decl() and not (self.peek()[1] in TYPES and self.peek(1)[0] == "name"):
            self.error("expected a declaration")
        typ, name = self.take("name"), self.take("name")
        if top and self.accept("("):
            params = []
            while not self.accept(")"):
                if params:
                    self.expect(",")
                ptype = self.take("name")
                if ptype not in TYPES:
                    self.i -= 1
                    self.error("expected a type")
                pname = self.take("name")
                params.append((ptype, pname, self.expr() if self.accept("=") else None))
            return ("func", typ, name, params, self.block(), frozenset(mods))
        value = self.expr() if self.accept("=") else None
        self.expect(";")
        return ("var", typ, name, value, frozenset(mods))

    def block(self):
        self.expect("{")
        body = []
        while not self.accept("}"):
            if self.peek()[0] == "end":
                self.error("expected '}'")
            body.append(self.stmt())
        return ("block", body)

    def stmt(self):
        _, v, _, _ = self.peek()
        if v == "{":
            return self.block()
        if self.is_decl():
            return self.decl()
        for word in ("break", "continue"):
            if self.accept(word):
                self.expect(";")
                return (word,)
        if self.accept("return"):
            value = None if self.peek()[1] == ";" else self.expr()
            self.expect(";")
            return ("return", value)
        if self.accept("if"):
            cond = self.paren()
            then = self.stmt()
            return ("if", cond, then, self.stmt() if self.accept("else") else None)
        if self.accept("while"):
            return ("while", self.paren(), self.stmt())
        if self.accept("for"):
            self.expect("(")
            var = self.take("name")
            self.expect("=")
            start = self.expr()
            self.expect(";")
            op = self.peek()[1] if self.peek()[1] in ("<", "<=", ">", ">=") else self.error("expected a comparison")
            self.i += 1
            limit = self.expr()
            self.expect(")")
            return ("for", var, start, op, limit, self.stmt())
        if self.accept("switch"):
            value = self.paren()
            self.expect("{")
            cases = []
            while not self.accept("}"):
                if self.accept("default"):
                    label = None
                else:
                    self.expect("case")
                    label = self.expr()
                self.expect(":")
                body = []
                while self.peek()[1] not in ("case", "default", "}") and self.peek()[0] != "end":
                    body.append(self.stmt())
                cases.append((label, body))
            return ("switch", value, cases)
        node = self.expr()
        self.expect(";")
        return ("expr", node)

    def paren(self):
        self.expect("(")
        node = self.expr()
        self.expect(")")
        return node

    def expr(self):
        left = self.binary(0)
        if self.accept("="):
            if left[0] != "name":
                self.i -= 1
                self.error("cannot assign to this")
            return ("assign", left[1], self.expr())
        return left

    def binary(self, level):
        if level == len(BINARY):
            return self.unary()
        left = self.binary(level + 1)
        while self.peek()[0] == "op" and self.peek()[1] in BINARY[level]:
            op = self.take("op")
            left = ("bin", op, left, self.binary(level + 1))
        return left

    def unary(self):
        for op in ("!", "-", "++", "--"):
            if self.accept(op):
                return ("unary", op, self.unary())
        node = self.primary()
        while self.peek()[1] in ("++", "--"):
            node = ("post", self.take("op"), node)
        return node

    def primary(self):
        kind, v, _, _ = self.peek()
        if kind == "num":
            return ("num", self.number())
        if kind == "str":
            return ("str", self.string())
        if v == "(":
            return self.paren()
        if kind == "name":
            self.i += 1
            if v in ("true", "false"):
                return ("bool", v == "true")
            if self.accept("("):
                args = []
                while not self.accept(")"):
                    if args:
                        self.expect(",")
                    args.append(self.expr())
                return ("call", v, args)
            return ("name", v)
        self.error("expected an expression")


def parse(text, path=None):
    """Return the top-level nodes of an XS script; raise XsError with the line on a syntax error."""
    return Parser(text, path).program()
