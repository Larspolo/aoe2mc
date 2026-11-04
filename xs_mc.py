"""XS script -> datapack functions (#5689, option B of #5120, docs/research/xs.md "XS as datapack functions").

Step 1: the `int` and `bool` globals, the operators and `main()`, with `xsSetTriggerVariable`, `xsTriggerVariable`
and `xsChatData`. Minecraft feature: datapack functions and scoreboards. A part with no datapack form skips its
statement and gives one warning line: the game program runs the whole script (game/scenario.py xs(), option A).
"""
import json
import re

OBJ = "aoe_xs"
VAR = "aoe_var"
DIR = "data/aoe2mc/function/xs"
# The game program sets #a while it runs the script itself (game/run.py freeze): the datapack form then does nothing.
TICK = f"execute unless score #a {OBJ} matches 1 unless score #main {OBJ} matches 1 if entity @a run function aoe2mc:xs/main"
LOAD = [f"scoreboard objectives add {OBJ} dummy", f"scoreboard objectives add {VAR} dummy"]
NUMBERS = ("int", "bool")
OPS = {"+": "+=", "-": "-=", "*": "*="}
COMPARE = {"<": "<", "<=": "<=", ">": ">", ">=": ">=", "==": "="}


class Skip(Exception):
    """A part with no datapack form: its word for the warning line."""


class Compiler:
    def __init__(self, text=None):
        self.text, self.k, self.ints, self.warnings, self.lines = text or "", 0, {}, [], []

    def warn(self, part):
        m = re.search(rf"\b{re.escape(part)}\b", self.text)
        line = self.text.count("\n", 0, m.start()) + 1 if m else 0
        w = f"XS script: {part} (line {line}): no datapack form, the game program runs it (game/run.py)"
        if w not in self.warnings:
            self.warnings.append(w)

    def temp(self):
        self.k += 1
        return f"#x{self.k} {OBJ}"

    def emit(self, line):
        self.lines.append(line)

    def copy(self, src):
        t = self.temp()
        self.emit(f"scoreboard players operation {t} = {src}")
        return t

    def holder(self, name):
        if name not in self.ints:
            raise Skip(name)
        return self.ints[name]

    def expr(self, node):
        """The lines of node; returns the holder ("<name> <objective>") of its value."""
        kind = node[0]
        if kind in ("num", "bool"):
            if isinstance(node[1], float):
                raise Skip("float")
            t = self.temp()
            self.emit(f"scoreboard players set {t} {int(node[1])}")
            return t
        if kind == "name":
            return self.holder(node[1])
        if kind == "assign":
            h, v = self.holder(node[1]), self.expr(node[2])
            self.emit(f"scoreboard players operation {h} = {v}")
            return h
        if kind == "unary":
            op, a = node[1], node[2]
            if op in ("++", "--"):
                return self.step(a, op)
            v, t = self.expr(a), self.temp()
            if op == "-":
                self.emit(f"scoreboard players set {t} 0")
                self.emit(f"scoreboard players operation {t} -= {v}")
            else:
                self.emit(f"execute store success score {t} if score {v} matches 0")
            return t
        if kind == "post":
            old = self.copy(self.holder(node[2][1]) if node[2][0] == "name" else self.expr(node[2]))
            self.step(node[2], node[1])
            return old
        if kind == "bin":
            return self.binary(*node[1:])
        if kind == "call":
            return self.call(node[1], node[2])
        raise Skip({"str": "string"}.get(kind, kind))

    def step(self, node, op):
        h = self.holder(node[1]) if node[0] == "name" else None
        if h is None:
            raise Skip(op)
        self.emit(f"scoreboard players {'add' if op == '++' else 'remove'} {h} 1")
        return h

    def binary(self, op, left, right):
        if op in ("&&", "||"):                 # no call or assignment on the right: both sides can run
            if pure(right) is False:
                raise Skip(op)
            a, b, t = self.expr(left), self.expr(right), self.temp()
            if op == "&&":
                self.emit(f"execute store success score {t} unless score {a} matches 0 unless score {b} matches 0")
            else:
                self.emit(f"execute store success score {t} unless score {a} matches 0")
                self.emit(f"execute unless score {b} matches 0 run scoreboard players set {t} 1")
            return t
        if op in ("/", "%"):                   # Minecraft rounds down, XS truncates toward zero as C
            a, b = self.expr(left), self.expr(right)
            q, m = self.copy(a), self.copy(a)
            self.emit(f"scoreboard players operation {q} /= {b}")
            self.emit(f"scoreboard players operation {m} %= {b}")      # a division by 0 keeps both scores
            fix = f"scoreboard players add {q} 1" if op == "/" else f"scoreboard players operation {m} -= {b}"
            for sa, sb in (("..-1", "1.."), ("0..", "..-1")):          # the signs differ and the rest is not 0
                self.emit(f"execute unless score {m} matches 0 if score {a} matches {sa} if score {b} matches {sb} run {fix}")
            return q if op == "/" else m
        a = self.copy(self.expr(left))
        b = self.expr(right)
        if op in OPS:
            self.emit(f"scoreboard players operation {a} {OPS[op]} {b}")
            return a
        if op in COMPARE or op == "!=":
            t = self.temp()
            self.emit(f"execute store success score {t} {'unless' if op == '!=' else 'if'} score {a} "
                      f"{COMPARE.get(op, '=')} {b}")
            return t
        raise Skip(op)

    def call(self, name, args):
        if name == "xsTriggerVariable" and len(args) == 1 and args[0][0] == "num" and isinstance(args[0][1], int):
            return f"#v{args[0][1]} {VAR}"
        if name == "xsSetTriggerVariable" and len(args) == 2 and args[0][0] == "num" and isinstance(args[0][1], int):
            v = self.expr(args[1])
            self.emit(f"scoreboard players operation #v{args[0][1]} {VAR} = {v}")
            return v
        if name == "xsChatData" and args and args[0][0] == "str" and len(args) <= 2:
            text = args[0][1]
            parts = [text]
            if len(args) == 2:
                v = self.expr(args[1])
                h, o = v.split()
                before, _, after = text.partition("%d") if "%d" in text else (text, "", "")
                parts = [before, {"score": {"name": h, "objective": o}}, after]
            self.emit("tellraw @a " + json.dumps([""] + [p for p in parts if p != ""]))
            return None
        raise Skip(name)

    def stmt(self, node, local):
        kind = node[0]
        if kind == "block":
            for s in node[1]:
                self.stmt(s, local)
            return
        before = len(self.lines)
        try:
            if kind == "var":
                _, typ, name, value, _ = node
                if typ not in NUMBERS:
                    raise Skip(typ)
                h = f"#{local}.{name} {OBJ}"
                v = self.expr(value) if value is not None else None
                self.ints[name] = h
                self.emit(f"scoreboard players operation {h} = {v}" if v else f"scoreboard players set {h} 0")
            elif kind == "expr":
                self.expr(node[1])
            else:
                raise Skip(kind)
        except Skip as e:
            del self.lines[before:]
            self.warn(str(e))


def pure(node):
    """False when node has a call or an assignment (they must not run when && or || stops early)."""
    if isinstance(node, tuple):
        if node and node[0] in ("call", "assign", "post") or node[:2] in (("unary", "++"), ("unary", "--")):
            return False
        return all(pure(x) is not False for x in node[1:])
    if isinstance(node, list):
        return all(pure(x) is not False for x in node)
    return True


def compile(tree, text=None):
    """(files, tick lines, load lines, warning lines) of the datapack form of the parsed script tree (xs.parse)."""
    c = Compiler(text)
    main = None
    for node in tree:
        if node[0] == "var":
            c.stmt(node, "g")
        elif node[0] == "func" and node[2] == "main" and not node[3]:
            main = node
        elif node[0] == "func":
            c.warn(node[2])
        elif node[0] == "rule":
            c.warn(node[1])
        else:
            c.warn(node[0])
    if main is not None:
        c.stmt(main[4], "l.main")
    c.emit(f"scoreboard players set #main {OBJ} 1")
    return {f"{DIR}/main.mcfunction": "\n".join(c.lines) + "\n"}, [TICK], list(LOAD), c.warnings
