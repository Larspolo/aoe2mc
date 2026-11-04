"""XS script -> datapack functions (#5689, option B of #5120, docs/research/xs.md "XS as datapack functions").

Step 6: `float` as a fixed point score (the value × 1000) and `vector` as three such holders `.x .y .z`, with the math and
vector functions of MATH (#5694). Minecraft feature: scoreboards (integers only). The trigonometric, `exp` and log
functions keep the warning line.
Step 4: the rules and the rule functions (#5692): `#now` counts the ticks; a rule R runs from its tick line when
`#on.R` is 1 and `#now` >= `#due.R`, then `#due.R` = `#now` + `#min.R` (ticks). Minecraft feature: the tick function and
scoreboards (no `schedule`: the world saves the scores).
Step 3: XS functions as `xs/f/<F>` with parameters `#l.F.<name>`, `static` locals `#s.F.<name>` and the return
value `#r.F`; `return` sets `#ret` and leaves (Minecraft feature: the `return` command, #5691). Recursion has no
datapack form (shared holders, no stack): the functions of a cycle give one warning line.
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
NOW = f"#now {OBJ}"
TICKS = 20
# The math and vector functions with a datapack form: name -> the numbers of arguments. One entry per line.
MATH = {
    "abs": (1,),
    "ceil": (1,),
    "degrees": (1,),
    "dist": (2,),
    "floor": (1,),
    "pow": (2,),
    "radians": (1,),
    "round": (1, 2),
    "sqrt": (1,),
    "vector": (3,),
    "xsCeilToInt": (1,),
    "xsVectorGetX": (1,),
    "xsVectorGetY": (1,),
    "xsVectorGetZ": (1,),
    "xsVectorLength": (1,),
    "xsVectorNormalize": (1,),
    "xsVectorSet": (3,),
    "xsVectorSetX": (2,),
    "xsVectorSetY": (2,),
    "xsVectorSetZ": (2,),
}
RULE_CALLS = ("xsDisableRule", "xsEnableRule", "xsIsRuleEnabled", "xsSetRuleMaxInterval", "xsSetRuleMinInterval")
GROUP_CALLS = ("xsDisableRuleGroup", "xsEnableRuleGroup", "xsIsRuleGroupEnabled")
SELF_CALLS = ("xsDisableSelf", "xsSetRuleMaxIntervalSelf", "xsSetRuleMinIntervalSelf")
COMPARE = {"<": "<", "<=": "<=", ">": ">", ">=": ">=", "==": "="}


class Skip(Exception):
    """A part with no datapack form: its word for the warning line."""


class Fx(str):
    """The holder of a float: a score of the value × 1000 (fixed point, #5694). A vector is a tuple of three."""


SCALE = 1000
DEG = 57296                 # 180 / pi × 1000: degrees() multiplies, radians() divides (0.001)
SQRT_STEPS = 24             # Newton steps from x / 2 + 0.5: enough for the range ±2 147 483
POW_MAX = 16


class Compiler:
    def __init__(self, text=None, civs=None):
        self.text, self.k, self.ints, self.warnings, self.lines = text or "", 0, {}, [], []
        self.civs, self.files = civs or {}, {}
        self.b, self.loops, self.breaks = 0, 0, 0    # sub-functions; loops and loops or switches around the code
        self.rules, self.current = {}, None          # {name: options}; the rule of the code
        self.consts, self.funcs, self.fn = {}, {}, None  # const values; compiled XS functions; current function

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
        if isinstance(src, tuple) or src is None:
            raise Skip("vector")
        t = self.temp()
        self.emit(f"scoreboard players operation {t} = {src}")
        return Fx(t) if isinstance(src, Fx) else t

    def vcopy(self, v):
        return tuple(self.copy(Fx(c)) for c in v) if isinstance(v, tuple) else self.copy(v)

    def to_f(self, h):
        """A float holder of h (an int × 1000)."""
        if isinstance(h, Fx):
            return h
        t = self.copy(h)
        self.emit(f"scoreboard players operation {t} *= {self.const(SCALE)}")
        return Fx(t)

    def to_i(self, h):
        """An int holder of h (a float truncates toward zero, as xs_run.convert)."""
        if isinstance(h, tuple) or h is None:
            raise Skip("vector")
        return self.idiv(str(h), self.const(SCALE), "/") if isinstance(h, Fx) else h

    def fit(self, target, v):
        """The value v for the holder target: the type of the target decides (int, float or vector)."""
        if isinstance(target, tuple) != isinstance(v, tuple):
            raise Skip("vector")
        if isinstance(target, tuple):
            return v
        return self.to_f(v) if isinstance(target, Fx) else self.to_i(v)

    def store(self, target, v):
        v = self.fit(target, v)
        for t, x in zip(target, v) if isinstance(target, tuple) else [(target, v)]:
            self.emit(f"scoreboard players operation {t} = {x}")
        return target

    def fmul(self, a, b):
        """a × b of two floats: (a / 1000) × b + (a % 1000) × b / 1000, so that a result that fits does not overflow."""
        a, b = self.to_f(a), self.to_f(b)
        q, r, c = self.copy(a), self.copy(a), self.const(SCALE)
        self.emit(f"scoreboard players operation {q} /= {c}")
        self.emit(f"scoreboard players operation {q} *= {b}")
        self.emit(f"scoreboard players operation {r} %= {c}")
        self.emit(f"scoreboard players operation {r} *= {b}")
        self.emit(f"scoreboard players operation {r} /= {c}")
        self.emit(f"scoreboard players operation {q} += {r}")
        return q

    def fdiv(self, a, b):
        """a / b of two floats: q = a / b, then q × 1000 + (a % b) × 1000 / b."""
        a, b = self.to_f(a), self.to_f(b)
        q, r, c = self.copy(a), self.copy(a), self.const(SCALE)
        self.emit(f"scoreboard players operation {q} /= {b}")
        self.emit(f"scoreboard players operation {q} *= {c}")
        self.emit(f"scoreboard players operation {r} %= {b}")
        self.emit(f"scoreboard players operation {r} *= {c}")
        self.emit(f"scoreboard players operation {r} /= {b}")
        self.emit(f"scoreboard players operation {q} += {r}")
        return q

    def idiv(self, a, b, op):
        """a / b or a % b of two ints: Minecraft rounds down, XS truncates toward zero as C."""
        q, m = self.copy(a), self.copy(a)
        self.emit(f"scoreboard players operation {q} /= {b}")
        self.emit(f"scoreboard players operation {m} %= {b}")      # a division by 0 keeps both scores
        fix = f"scoreboard players add {q} 1" if op == "/" else f"scoreboard players operation {m} -= {b}"
        for sa, sb in (("..-1", "1.."), ("0..", "..-1")):          # the signs differ and the rest is not 0
            self.emit(f"execute unless score {m} matches 0 if score {a} matches {sa} if score {b} matches {sb} run {fix}")
        return q if op == "/" else m

    def holder(self, name):
        if name not in self.ints:
            raise Skip(name)
        return self.ints[name]

    def expr(self, node):
        """The lines of node; returns the holder ("<name> <objective>") of its value."""
        kind = node[0]
        if kind in ("num", "bool"):
            t = self.temp()
            if isinstance(node[1], float):
                self.emit(f"scoreboard players set {t} {round(node[1] * SCALE)}")
                return Fx(t)
            self.emit(f"scoreboard players set {t} {int(node[1])}")
            return t
        if kind == "name":
            if node[1] in self.consts:             # const: its value goes into each use
                return self.expr(self.consts[node[1]])
            return self.holder(node[1])
        if kind == "assign":
            return self.store(self.holder(node[1]), self.expr(node[2]))
        if kind == "unary":
            op, a = node[1], node[2]
            if op in ("++", "--"):
                return self.step(a, op)
            v = self.expr(a)
            if op == "-":
                if isinstance(v, tuple):
                    return tuple(self.binary("-", ("num", 0.0), ("h", Fx(c))) for c in v)
                t = self.temp()
                self.emit(f"scoreboard players set {t} 0")
                self.emit(f"scoreboard players operation {t} -= {v}")
                return Fx(t) if isinstance(v, Fx) else t
            t = self.temp()
            if isinstance(v, tuple):
                raise Skip("vector")
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
        if kind == "h":                            # a holder of the compiler (a part of a vector)
            return node[1]
        raise Skip({"str": "string"}.get(kind, kind))

    def step(self, node, op):
        h = self.holder(node[1]) if node[0] == "name" else None
        if h is None or isinstance(h, tuple):
            raise Skip(op)
        self.emit(f"scoreboard players {'add' if op == '++' else 'remove'} {h} {SCALE if isinstance(h, Fx) else 1}")
        return h

    def binary(self, op, left, right):
        if op in ("&&", "||"):
            if pure(right) is False:           # a sub-function runs the right side only when needed (short circuit)
                a, t = self.expr(left), self.temp()
                self.emit(f"execute store success score {t} unless score {a} matches 0")

                def rhs():
                    b = self.expr(right)
                    self.emit(f"execute store success score {t} unless score {b} matches 0")
                self.emit(f"execute {'unless' if op == '&&' else 'if'} score {t} matches 0 run function {self.sub(rhs)}")
                return t
            a, b, t = self.expr(left), self.expr(right), self.temp()
            if op == "&&":
                self.emit(f"execute store success score {t} unless score {a} matches 0 unless score {b} matches 0")
            else:
                self.emit(f"execute store success score {t} unless score {a} matches 0")
                self.emit(f"execute unless score {b} matches 0 run scoreboard players set {t} 1")
            return t
        if op in ("/", "%"):
            a, b = self.expr(left), self.expr(right)
            if typed(a) or typed(b):
                return self.typed(op, a, b)
            return self.idiv(a, b, op)
        a = self.vcopy(self.expr(left))
        b = self.expr(right)
        if typed(a) or typed(b):
            return self.typed(op, a, b)
        if op in OPS:
            self.emit(f"scoreboard players operation {a} {OPS[op]} {b}")
            return a
        if op in COMPARE or op == "!=":
            t = self.temp()
            self.emit(f"execute store success score {t} {'unless' if op == '!=' else 'if'} score {a} "
                      f"{COMPARE.get(op, '=')} {b}")
            return t
        raise Skip(op)

    def typed(self, op, a, b):
        """op of a float or vector and another value: fixed point on each part."""
        if isinstance(a, tuple) or isinstance(b, tuple):
            if op in ("+", "-") and isinstance(a, tuple) and isinstance(b, tuple):
                return tuple(self.typed(op, Fx(x), Fx(y)) for x, y in zip(a, b))
            if op in ("*", "/") and isinstance(a, tuple) and not isinstance(b, tuple):
                return tuple(self.typed(op, Fx(x), b) for x in a)
            if op == "*" and isinstance(b, tuple) and not isinstance(a, tuple):
                return tuple(self.typed(op, a, Fx(y)) for y in b)
            if op in ("==", "!=") and isinstance(a, tuple) and isinstance(b, tuple):
                t = self.temp()
                self.emit(f"execute store success score {t} " + " ".join(f"if score {x} = {y}" for x, y in zip(a, b)))
                if op == "!=":
                    self.emit(f"execute store success score {t} if score {t} matches 0")
                return t
            raise Skip("vector")
        a, b = self.to_f(a), self.to_f(b)
        if op == "*":
            return self.fmul(a, b)
        if op == "/":
            return self.fdiv(a, b)
        if op == "%":                          # fmod: the int rest of the two scores
            return Fx(self.idiv(a, b, "%"))
        if op in ("+", "-"):
            t = self.copy(a)
            self.emit(f"scoreboard players operation {t} {OPS[op]} {b}")
            return t
        if op in COMPARE or op == "!=":
            t = self.temp()
            self.emit(f"execute store success score {t} {'unless' if op == '!=' else 'if'} score {a} "
                      f"{COMPARE.get(op, '=')} {b}")
            return t
        raise Skip(op)

    def call(self, name, args):
        if name in self.funcs:
            return self.xs_call(name, args)
        if name == "xsTriggerVariable" and len(args) == 1 and args[0][0] == "num" and isinstance(args[0][1], int):
            return f"#v{args[0][1]} {VAR}"
        if name == "xsSetTriggerVariable" and len(args) == 2 and args[0][0] == "num" and isinstance(args[0][1], int):
            v = self.to_i(self.expr(args[1]))
            self.emit(f"scoreboard players operation #v{args[0][1]} {VAR} = {v}")
            return v
        if name == "xsChatData" and args and args[0][0] == "str" and len(args) <= 2:
            text = args[0][1]
            parts = [text]
            if len(args) == 2:
                v = self.to_i(self.expr(args[1]))       # a float shows its whole part
                h, o = v.split()
                before, _, after = text.partition("%d") if "%d" in text else (text, "", "")
                parts = [before, {"score": {"name": h, "objective": o}}, after]
            self.emit("tellraw @a " + json.dumps([""] + [p for p in parts if p != ""]))
            return None
        if name in MATH:
            return self.math(name, args)
        if name in RULE_CALLS + GROUP_CALLS + SELF_CALLS:
            return self.rule_call(name, args)
        if name in ("xsGetTime", "xsGetGameTime") and not args:
            t = self.copy(NOW)
            self.emit(f"scoreboard players operation {t} {'*=' if name == 'xsGetTime' else '/='} "
                      f"{self.const(1000 // TICKS if name == 'xsGetTime' else TICKS)}")
            return t
        if name in ("xsGetObjectCount", "xsGetObjectCountTotal") and len(args) == 2:
            return self.count(*args)
        if name == "xsGetPlayerCivilization" and len(args) == 1 and literal(args[0]):
            t = self.temp()
            self.emit(f"scoreboard players set {t} {civ_id(self.civs.get(args[0][1]))}")
            return t
        raise Skip(name)

    def math(self, name, args):
        """The math and vector functions of MATH on fixed point holders (#5694)."""
        n = len(args) == 2 and number(args[1])
        if len(args) not in MATH[name] or (name == "pow" and not (n is not None and abs(n) <= POW_MAX)):
            raise Skip(name)
        if name == "pow":
            x, r = self.to_f(self.expr(args[0])), self.expr(("num", 1.0))
            for _ in range(abs(n)):
                r = self.fmul(r, x)
            return r if n >= 0 else self.fdiv(self.expr(("num", 1.0)), r)
        if name == "round" and len(args) == 2 and not (literal(args[1]) and 0 <= args[1][1] <= 3):
            raise Skip(name)
        vs = [self.expr(a) for a in args]
        if name in ("vector", "xsVectorSet"):
            return tuple(self.copy(self.to_f(v)) for v in vs)
        if name.startswith(("xsVectorGet", "xsVectorSet")):
            if not isinstance(vs[0], tuple):
                raise Skip(name)
            i = "XYZ".index(name[-1])
            if name.startswith("xsVectorGet"):
                return self.copy(Fx(vs[0][i]))
            out = list(self.vcopy(vs[0]))
            out[i] = self.copy(self.to_f(vs[1]))
            return tuple(out)
        if name == "dist":
            vs = [self.typed("-", *vs)]
        if name in ("dist", "xsVectorLength", "xsVectorNormalize"):
            if not isinstance(vs[0], tuple):
                raise Skip(name)
            sq = self.expr(("num", 0.0))
            for c in vs[0]:
                self.emit(f"scoreboard players operation {sq} += {self.fmul(Fx(c), Fx(c))}")
            n = self.sqrt(sq)
            if name != "xsVectorNormalize":
                return n
            out = tuple(self.fdiv(Fx(c), n) for c in vs[0])
            for c in out:                              # a zero vector stays zero (as xs_run.normalize)
                self.emit(f"execute if score {n} matches 0 run scoreboard players set {c} 0")
            return out
        x = self.to_f(vs[0])
        if name == "abs":
            t = self.copy(x)
            self.emit(f"execute if score {t} matches ..-1 run scoreboard players operation {t} *= {self.const(-1)}")
            return t
        if name == "sqrt":
            return self.sqrt(x)
        if name == "degrees":
            return self.fmul(x, self.expr(("num", DEG / SCALE)))
        if name == "radians":
            return self.fdiv(x, self.expr(("num", DEG / SCALE)))
        unit = SCALE // 10 ** args[1][1] if name == "round" and len(args) == 2 else SCALE
        t, u = self.copy(x), self.const(unit)
        if name in ("ceil", "xsCeilToInt"):            # Minecraft rounds down: ceil(x) = floor(x + 0.999)
            self.emit(f"scoreboard players add {t} {unit - 1}")
        elif name == "round":                          # half away from zero is a choice: XS does not say more
            self.emit(f"scoreboard players add {t} {unit // 2}")
        self.emit(f"scoreboard players operation {t} /= {u}")
        if name == "xsCeilToInt":
            return str(t)
        self.emit(f"scoreboard players operation {t} *= {u}")
        return t

    def sqrt(self, x):
        """An integer square root by Newton steps: the function xs/sqrt with a fixed number of steps (0.001)."""
        a, y = f"#sq.a {OBJ}", f"#sq.y {OBJ}"
        if f"{DIR}/sqrt.mcfunction" not in self.files:
            outer, self.lines = self.lines, []
            try:
                self.emit(f"scoreboard players set {y} 0")
                self.emit(f"execute if score {a} matches ..0 run return 0")
                self.emit(f"scoreboard players operation {y} = {a}")
                self.emit(f"scoreboard players operation {y} /= {self.const(2)}")
                self.emit(f"scoreboard players add {y} {SCALE // 2}")
                for _ in range(SQRT_STEPS):             # y = (y + a / y) / 2
                    q = self.fdiv(Fx(a), Fx(y))
                    self.emit(f"scoreboard players operation {y} += {q}")
                    self.emit(f"scoreboard players operation {y} /= {self.const(2)}")
                self.files[f"{DIR}/sqrt.mcfunction"] = "\n".join(self.lines) + "\n"
            finally:
                self.lines = outer
        self.emit(f"scoreboard players operation {a} = {x}")
        self.emit("function aoe2mc:xs/sqrt")
        return self.copy(Fx(y))

    def const(self, n):
        self.emit(f"scoreboard players set #c{n} {OBJ} {n}")
        return f"#c{n} {OBJ}"

    def rule_call(self, name, args):
        """The rule functions with a literal rule or group name (a computed name: a warning)."""
        self_ = name.endswith("Self")
        if self_:
            if self.current is None:
                raise Skip(name)
            rules = [self.current]
        else:
            if not args or args[0][0] != "str":
                raise Skip(name)
            key, args = args[0][1], args[1:]
            rules = ([n for n, o in self.rules.items() if o.get("group") == key] if name in GROUP_CALLS
                     else [key] if key in self.rules else None)
            if rules is None:
                raise Skip(name)
        base = name.removesuffix("Self").replace("RuleGroup", "Rule")
        if base == "xsIsRuleEnabled":
            t = self.temp()
            self.emit(f"scoreboard players set {t} 0")
            for r in rules:
                self.emit(f"execute if score #on.{r} {OBJ} matches 1 run scoreboard players set {t} 1")
            return t
        if base in ("xsSetRuleMinInterval", "xsSetRuleMaxInterval"):
            if len(args) != 1:
                raise Skip(name)
            v = self.copy(self.expr(args[0]))
            self.emit(f"scoreboard players operation {v} *= {self.const(TICKS)}")
            for r in rules:
                self.emit(f"scoreboard players operation #{'mi' if 'Min' in base else 'ma'}.{r} {OBJ} = {v}")
                self.interval(r)
            return None
        if args:
            raise Skip(name)
        for r in rules:
            if base == "xsEnableRule":
                self.emit(f"execute unless score #on.{r} {OBJ} matches 1 run scoreboard players operation #due.{r} {OBJ} = {NOW}")
                if not self.rules[r].get("runImmediately"):
                    self.emit(f"execute unless score #on.{r} {OBJ} matches 1 run "
                              f"scoreboard players operation #due.{r} {OBJ} += #min.{r} {OBJ}")
            self.emit(f"scoreboard players set #on.{r} {OBJ} {int(base == 'xsEnableRule')}")
        return None

    def interval(self, r):
        """#min.R = min(minInterval, maxInterval) in ticks."""
        self.emit(f"scoreboard players operation #min.{r} {OBJ} = #mi.{r} {OBJ}")
        self.emit(f"scoreboard players operation #min.{r} {OBJ} < #ma.{r} {OBJ}")

    def rule(self, node):
        """The function xs/r/<name> of a rule and its tick line."""
        _, name, opts, block = node
        self.current, outer, self.lines = name, self.lines, []
        try:
            if not opts.get("highFrequency"):
                self.emit(f"scoreboard players operation #due.{name} {OBJ} = {NOW}")
                self.emit(f"scoreboard players operation #due.{name} {OBJ} += #min.{name} {OBJ}")
            self.stmt(block, f"r.{name}")
            self.files[f"{DIR}/r/{name}.mcfunction"] = "\n".join(self.lines) + "\n"
        finally:
            self.lines, self.current = outer, None
        due = "" if opts.get("highFrequency") else f" if score {NOW} >= #due.{name} {OBJ}"
        return f"execute if score #on.{name} {OBJ} matches 1{due} run function aoe2mc:xs/r/{name}"

    def start(self):
        """The rule scores at the start (before main())."""
        for name, o in self.rules.items():
            self.emit(f"scoreboard players set #on.{name} {OBJ} {int(not o.get('inactive'))}")
            self.emit(f"scoreboard players set #mi.{name} {OBJ} {round(o.get('minInterval', 1) * TICKS)}")
            mx = o.get("maxInterval")
            self.emit(f"scoreboard players set #ma.{name} {OBJ} {2**31 - 1 if mx is None else round(mx * TICKS)}")
            self.interval(name)
            self.emit(f"scoreboard players operation #due.{name} {OBJ} = {NOW}")
            if not o.get("runImmediately"):
                self.emit(f"scoreboard players operation #due.{name} {OBJ} += #min.{name} {OBJ}")

    def xs_call(self, name, args):
        """A call of an XS function: the arguments into its parameters, then the function (no stack: no recursion)."""
        params, typ = self.funcs[name]
        if len(args) > len(params):
            raise Skip(name)
        vals = [self.copy(self.expr(a)) for a in args]       # all arguments first: one can read a parameter
        for i, (_, p, default) in enumerate(params):
            h = f"#l.{name}.{p} {OBJ}"
            if i < len(vals):
                self.emit(f"scoreboard players operation {h} = {self.to_i(vals[i])}")
            elif default is not None:
                self.emit(f"scoreboard players operation {h} = {self.expr(default)}")
            else:
                self.emit(f"scoreboard players set {h} 0")
        self.emit(f"function aoe2mc:xs/f/{name}")
        self.emit(f"scoreboard players set #ret {OBJ} 0")
        return self.copy(f"#r.{name} {OBJ}") if typ in NUMBERS else None

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
        """After a sub-function: leave the current function when a return, break or continue is set."""
        if self.fn:
            self.emit(f"execute if score #ret {OBJ} matches 1 run return 0")
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
            if isinstance(c, tuple):
                raise Skip("vector")
            self.emit(f"execute if score {c} matches 0 run return 0")
            self.emit(f"function {self.body(body, local, 1)}")
            if self.fn:
                self.emit(f"execute if score #ret {OBJ} matches 1 run return 0")
            self.emit(f"scoreboard players set #cont {OBJ} 0")
            self.emit(f"execute if score #brk {OBJ} matches 1 run return run scoreboard players set #brk {OBJ} 0")
            if step:
                step()
            self.emit(f"function {name}")
        self.emit(f"function {self.sub(run)}")
        if self.fn:
            self.emit(f"execute if score #ret {OBJ} matches 1 run return 0")

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
            self.flags()
        elif kind == "return":
            if self.fn is None:
                raise Skip("return")
            if node[1] is not None:
                v = self.to_i(self.expr(node[1]))
                self.emit(f"scoreboard players operation #r.{self.fn} {OBJ} = {v}")
            self.emit(f"scoreboard players set #ret {OBJ} 1")
            self.emit("return 0")
        elif kind in ("break", "continue"):
            if not (self.loops if kind == "continue" else self.breaks):
                raise Skip(kind)
            self.emit(f"scoreboard players set #{'cont' if kind == 'continue' else 'brk'} {OBJ} 1")
            self.emit("return 0")
        else:
            raise Skip(kind)

    def function(self, node):
        """xs/f/<F>: the body of an XS function with its own holders."""
        name, ints, consts, outer = node[2], dict(self.ints), dict(self.consts), self.lines
        self.ints.update({p: f"#l.{name}.{p} {OBJ}" for _, p, _ in node[3]})
        self.fn, self.lines = name, []
        try:
            self.stmt(node[4], f"l.{name}")
            self.files[f"{DIR}/f/{name}.mcfunction"] = "\n".join(self.lines) + "\n"
        finally:
            self.fn, self.lines, self.ints, self.consts = None, outer, ints, consts

    def init(self, h, value, done=False):
        """Set the new holder h to value (a tree node, or with done a holder), else to 0."""
        v = value if done or value is None else self.expr(value)
        if v is None:
            for t in h if isinstance(h, tuple) else [h]:
                self.emit(f"scoreboard players set {t} 0")
        else:
            self.store(h, v)

    def stmt(self, node, local):
        kind = node[0]
        if kind == "block":
            for s in node[1]:
                self.stmt(s, local)
            return
        before, files, b = len(self.lines), dict(self.files), self.b
        try:
            if kind == "var":
                _, typ, name, value, mods = node
                if typ not in NUMBERS + ("float", "vector"):
                    raise Skip(typ)
                if "const" in mods and value is not None:
                    self.consts[name] = value
                    return
                if "static" in mods and self.fn:  # set once: a flag holder marks the first run
                    h = make(typ, f"#s.{self.fn}.{name}")

                    def init():
                        self.init(h, value)
                        self.emit(f"scoreboard players set #s.{self.fn}.{name}.i {OBJ} 1")
                    sub = self.sub(init)
                    self.ints[name] = h
                    self.emit(f"execute unless score #s.{self.fn}.{name}.i {OBJ} matches 1 run function {sub}")
                    return
                h = make(typ, f"#{local}.{name}")
                v = self.fit(h, self.expr(value)) if value is not None else None
                self.ints[name] = h
                self.init(h, v, done=True)
            elif kind == "expr":
                self.expr(node[1])
            else:
                self.control(node, local)
        except Skip as e:
            del self.lines[before:]
            self.files, self.b = files, b
            self.warn(str(e))


def calls(node):
    """The names of the calls in node."""
    if isinstance(node, tuple):
        own = {node[1]} if node[:1] == ("call",) else set()
        return own.union(*(calls(x) for x in node[1:]))
    if isinstance(node, list):
        return set().union(*(calls(x) for x in node))
    return set()


def cycles(graph):
    """The names that can reach themselves through the call graph {name: called names}."""
    out = set()
    for start in graph:
        seen, todo = set(), list(graph[start])
        while todo:
            n = todo.pop()
            if n == start:
                out.add(start)
                break
            if n in graph and n not in seen:
                seen.add(n)
                todo.extend(graph[n])
    return out


def make(typ, base):
    """The holder of a new variable of the type typ: a vector has three float holders .x .y .z."""
    if typ == "vector":
        return tuple(Fx(f"{base}.{c} {OBJ}") for c in "xyz")
    return Fx(f"{base} {OBJ}") if typ == "float" else f"{base} {OBJ}"


def typed(h):
    return isinstance(h, (Fx, tuple))


def number(node):
    """The int of a literal int, also with a minus (pow(x, -2)), else None."""
    if node[:2] == ("unary", "-"):
        n = number(node[2])
        return None if n is None else -n
    return node[1] if literal(node) else None


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
    rules = [n for n in tree if n[0] == "rule" and re.fullmatch(r"[A-Za-z0-9_]+", n[1])]
    c.rules = {n[1]: n[2] for n in rules}
    funcs = {n[2]: n for n in tree if n[0] == "func" and n[2] != "main"}
    bad = cycles({k: calls(f[4]) for k, f in funcs.items()})
    for name, f in funcs.items():
        if name not in bad and f[1] in NUMBERS + ("void",) and all(p[0] in NUMBERS for p in f[3]):
            c.funcs[name] = (f[3], f[1])
    for node in tree:
        if node[0] == "var":
            c.stmt(node, "g")
        elif node[0] == "func" and node[2] == "main" and not node[3]:
            main = node
        elif node[0] == "func" and node[2] in c.funcs:
            c.function(node)
        elif node[0] == "func":
            c.warn(node[2])
        elif node[0] == "rule":
            if node[1] not in c.rules:
                c.warn(node[1])
        else:
            c.warn(node[0])
    c.start()
    if main is not None:
        c.stmt(main[4], "l.main")
    c.emit(f"scoreboard players set #main {OBJ} 1")
    lines, c.lines = c.lines, []
    order = sorted(range(len(rules)), key=lambda i: (-rules[i][2].get("priority", 0), i))
    tick = [TICK] + [c.rule(rules[i]) for i in order] + [f"scoreboard players add {NOW} 1"]
    return {f"{DIR}/main.mcfunction": "\n".join(lines) + "\n"} | c.files, tick, list(LOAD), c.warnings


def snippet(code, name):
    """(files, function, holder, warnings) of the XS code of one "Script Call" (#5693): compile() under xs/<name>/, and the
    first function of the code (not main) to run, with the holder of its return value. No such function: no function,
    and the game program runs the code (its warnings say why)."""
    import xs
    try:
        tree = xs.parse(code, name)
    except xs.XsError as e:
        return {}, None, None, [f"XS script: {e}: no datapack form, the game program runs it (game/run.py)"]
    files, _, _, warnings = compile(tree, code)
    first = next((n[2] for n in tree if n[0] == "func" and n[2] != "main"), None)
    if first is None or f"{DIR}/f/{first}.mcfunction" not in files:
        return {}, None, None, warnings
    # the names of one code do not clash with the other codes or the map script: the prefix goes into every path
    out = {k.replace(f"{DIR}/", f"{DIR}/{name}/", 1): v.replace("aoe2mc:xs/", f"aoe2mc:xs/{name}/") for k, v in files.items()}
    return out, f"aoe2mc:xs/{name}/f/{first}", f"#r.{first}", warnings
