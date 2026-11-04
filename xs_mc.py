"""XS script -> datapack functions (#5689, option B of #5120, docs/research/xs.md "XS as datapack functions").

Step 7: `xsGetObjectCount`, `xsGetObjectCountTotal` (an entity count) and `xsGetPlayerCivilization` (a constant, #5695).
Step 2: `if`, `else`, `while`, `for`, `break`, `continue` and `switch` as sub-functions `xs/b/<k>` (#5690).
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
STORE = "aoe2mc:xs"
MOUNT = "aoe2mc.mount"      # units.MOUNT: the horse of a unit does not count (as aoe2mc.area_selector)
# A computed player or type: a macro function puts them into the selector (Minecraft feature: macro functions).
COUNT = f"$return run execute if entity @e[tag=aoe2mc.p$(p),tag=aoe2mc.t$(id),tag=!{MOUNT}]"
COMPARE = {"<": "<", "<=": "<=", ">": ">", ">=": ">=", "==": "="}


class Skip(Exception):
    """A part with no datapack form: its word for the warning line."""


class Compiler:
    def __init__(self, text=None, civs=None):
        self.text, self.k, self.ints, self.warnings, self.lines = text or "", 0, {}, [], []
        self.civs, self.files = civs or {}, {}
        self.b, self.loops, self.breaks = 0, 0, 0    # sub-functions; loops and loops or switches around the code

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
        if name in ("xsGetObjectCount", "xsGetObjectCountTotal") and len(args) == 2:
            return self.count(*args)
        if name == "xsGetPlayerCivilization" and len(args) == 1 and literal(args[0]):
            t = self.temp()
            self.emit(f"scoreboard players set {t} {civ_id(self.civs.get(args[0][1]))}")
            return t
        raise Skip(name)

    def count(self, player, kind):
        """The units of a player and type (no queue or site in a vanilla world: the total is the same count)."""
        t = self.temp()
        if literal(player) and literal(kind):
            self.emit(f"execute store result score {t} if entity "
                      f"@e[tag=aoe2mc.p{player[1]},tag=aoe2mc.t{kind[1]},tag=!{MOUNT}]")
            return t
        for key, node in (("p", player), ("id", kind)):
            if literal(node):
                self.emit(f"data modify storage {STORE} count.{key} set value {node[1]}")
            else:
                v = self.expr(node)
                self.emit(f"execute store result storage {STORE} count.{key} int 1 run scoreboard players get {v}")
        self.files[f"{DIR}/count.mcfunction"] = COUNT + "\n"
        self.emit(f"execute store result score {t} run function aoe2mc:xs/count with storage {STORE} count")
        return t

    def sub(self, body):
        """A new sub-function xs/b/<k> with the lines of body(); returns its name."""
        self.b += 1
        k, outer, self.lines = self.b, self.lines, []
        try:
            body()
            self.files[f"{DIR}/b/{k}.mcfunction"] = "\n".join(self.lines) + "\n"
        finally:
            self.lines = outer
        return f"aoe2mc:xs/b/{k}"

    def flags(self):
        """After a sub-function: leave the current function when a break or continue is set."""
        if self.breaks:
            for f in ("brk", "cont") if self.loops else ("brk",):
                self.emit(f"execute if score #{f} {OBJ} matches 1 run return 0")

    def body(self, node, local, loop):
        def run():
            self.loops += loop
            self.breaks += 1
            try:
                self.stmt(node, local)
            finally:
                self.loops -= loop
                self.breaks -= 1
        return self.sub(run)

    def loop(self, cond, body, local, step=None):
        """A loop: a sub-function that tests the condition, runs the body and calls itself (Minecraft feature)."""
        name = f"aoe2mc:xs/b/{self.b + 1}"

        def run():
            c = self.expr(cond)
            self.emit(f"execute if score {c} matches 0 run return 0")
            self.emit(f"function {self.body(body, local, 1)}")
            self.emit(f"scoreboard players set #cont {OBJ} 0")
            self.emit(f"execute if score #brk {OBJ} matches 1 run return run scoreboard players set #brk {OBJ} 0")
            if step:
                step()
            self.emit(f"function {name}")
        self.emit(f"function {self.sub(run)}")

    def control(self, node, local):
        kind = node[0]
        if kind == "if":
            c = self.copy(self.expr(node[1]))       # the body can change a variable of the condition
            self.emit(f"execute unless score {c} matches 0 run function {self.body(node[2], local, 0)}")
            if node[3] is not None:
                self.emit(f"execute if score {c} matches 0 run function {self.body(node[3], local, 0)}")
            self.flags()
        elif kind == "while":
            self.loop(node[1], node[2], local)
        elif kind == "for":
            _, var, start, op, limit, body = node
            h = self.ints.setdefault(var, f"#{local}.{var} {OBJ}")
            self.emit(f"scoreboard players operation {h} = {self.expr(start)}")
            self.loop(("bin", op, ("name", var), limit), body, local,
                      lambda: self.emit(f"scoreboard players {'add' if op in ('<', '<=') else 'remove'} {h} 1"))
        elif kind == "switch":
            # As game/xs_run.py: the first case with the value (else default) runs, no fall through
            v, hit = self.expr(node[1]), self.temp()
            self.emit(f"scoreboard players set {hit} 0")
            for i, (label, _) in enumerate(node[2], 1):
                if label is not None and not literal(label):
                    raise Skip("case")
                test = f" if score {v} matches {label[1]}" if label is not None else ""
                if label is not None:
                    self.emit(f"execute if score {hit} matches 0{test} run scoreboard players set {hit} {i}")
            for i, (label, _) in enumerate(node[2], 1):
                if label is None:
                    self.emit(f"execute if score {hit} matches 0 run scoreboard players set {hit} {i}")
            for i, (_, stmts) in enumerate(node[2], 1):
                self.emit(f"execute if score {hit} matches {i} run function {self.body(('block', stmts), local, 0)}")
            self.emit(f"scoreboard players set #brk {OBJ} 0")
            if self.breaks:
                self.flags()
        elif kind in ("break", "continue"):
            if not (self.loops if kind == "continue" else self.breaks):
                raise Skip(kind)
            self.emit(f"scoreboard players set #{'cont' if kind == 'continue' else 'brk'} {OBJ} 1")
            self.emit("return 0")
        else:
            raise Skip(kind)

    def stmt(self, node, local):
        kind = node[0]
        if kind == "block":
            for s in node[1]:
                self.stmt(s, local)
            return
        before, files, b = len(self.lines), dict(self.files), self.b
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
                self.control(node, local)
        except Skip as e:
            del self.lines[before:]
            self.files, self.b = files, b
            self.warn(str(e))


def literal(node):
    return node[0] == "num" and isinstance(node[1], int)


def civ_id(name):
    """The AoE2 civilization ID of a civilization key, as game/xs_host.civ_id (the .dat order), else 0."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return next((i for i, c in enumerate(Civilization) if c.name == name), 0)


def pure(node):
    """False when node has a call or an assignment (they must not run when && or || stops early)."""
    if isinstance(node, tuple):
        if node and node[0] in ("call", "assign", "post") or node[:2] in (("unary", "++"), ("unary", "--")):
            return False
        return all(pure(x) is not False for x in node[1:])
    if isinstance(node, list):
        return all(pure(x) is not False for x in node)
    return True


def compile(tree, text=None, civs=None):
    """(files, tick lines, load lines, warning lines) of the datapack form of the parsed script tree (xs.parse).
    civs: {player: civilization key} of the converted map (xsGetPlayerCivilization)."""
    c = Compiler(text, civs)
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
    return {f"{DIR}/main.mcfunction": "\n".join(c.lines) + "\n"} | c.files, [TICK], list(LOAD), c.warnings
