"""Run an XS script of AoE2 DE in the game program (#5610, epic #5119, option A of #5120).

`xs.parse` gives the tree; `Xs` walks it. The game program calls `tick(now)` with the game time in seconds: the first
tick calls `main()`, then each enabled rule that is due runs (a higher `priority` first). Minecraft has no script
language that can run XS code, so this is own logic (the datapack compile is option B of #5120).
The built-in functions are the control, math and vector functions of the XS function list (the signatures of
`xs-check` in AoE2ScenarioParser); the game functions come through `host` (name -> callable). An unknown name gives
one warning line and the script goes on; a runtime error or the step limit stops only the current call.
Rule times (a choice where AoE2 does not say more): a rule enabled at time t first runs at t + minInterval, at t with
`runImmediately` (also in the tick of a rule that enables it), and at each tick with `highFrequency`; then each
min(minInterval, maxInterval) seconds. The default minInterval is 1 second.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import xs  # noqa: E402

STEPS = 200000                                   # statements and loop turns in one call: a script must not stop the server
DEFAULT = {"int": 0, "float": 0.0, "bool": False, "string": "", "vector": (0.0, 0.0, 0.0), "void": None}


class XsRunError(Exception):
    pass


class Flow(Exception):                           # break, continue and return go up the Python stack
    def __init__(self, kind, value=None):
        self.kind, self.value = kind, value


def int32(v):
    return (int(v) + 2 ** 31) % 2 ** 32 - 2 ** 31


def text(v):
    """A value as XS writes it in a string."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:f}"
    if isinstance(v, tuple):
        return "(" + ", ".join(f"{c:f}" for c in v) + ")"
    return str(v)


def convert(typ, v):
    """The value of an assignment to a variable, parameter or return of type typ."""
    if typ == "void" or v is None:
        return DEFAULT.get(typ)
    if typ == "string":
        return v if isinstance(v, str) else text(v)
    if isinstance(v, tuple) != (typ == "vector") or isinstance(v, str):
        raise XsRunError(f"cannot convert {text(v)!r} to {typ}")
    return {"int": int32, "float": float, "bool": bool, "vector": vec}[typ](v)


def binary(op, a, b):
    if op == "+" and (isinstance(a, str) or isinstance(b, str)):
        return text(a) + text(b)
    if op in ("==", "!="):
        return (a == b) == (op == "==")
    if isinstance(a, tuple) or isinstance(b, tuple):       # vector + vector, vector * number
        if op in ("+", "-") and isinstance(a, tuple) and isinstance(b, tuple):
            return tuple(x + y if op == "+" else x - y for x, y in zip(a, b))
        if op in ("*", "/") and isinstance(a, tuple) and not isinstance(b, tuple):
            return tuple(x * b if op == "*" else x / b for x in a)
        if op == "*" and isinstance(b, tuple):
            return tuple(a * y for y in b)
        raise XsRunError(f"no {op} for {text(a)} and {text(b)}")
    if isinstance(a, str) or isinstance(b, str):
        if op in ("<", "<=", ">", ">=") and isinstance(a, str) and isinstance(b, str):
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        raise XsRunError(f"no {op} for {text(a)!r} and {text(b)!r}")
    if op in ("<", "<=", ">", ">="):
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    ints = not isinstance(a, float) and not isinstance(b, float)
    if op in ("/", "%") and b == 0:
        raise XsRunError("division by zero")
    if op == "/":                                # int / int truncates toward zero, as C
        return int32(abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)) if ints else a / b
    if op == "%":
        return int32(math.fmod(a, b)) if ints else math.fmod(a, b)
    r = {"+": a + b, "-": a - b, "*": a * b}[op]
    return int32(r) if ints else float(r)


def vec(v):
    return tuple(map(float, v))


def normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return vec(c / n for c in v) if n else (0.0, 0.0, 0.0)


# The built-in functions without the game: name -> function(run, *args). One entry per line, in alphabetical order.
BUILTIN = {
    "abs": lambda r, x: float(abs(x)),
    "acos": lambda r, x: math.acos(x),
    "asin": lambda r, x: math.asin(x),
    "atan": lambda r, x: math.atan(x),
    "atan2": lambda r, y, x: math.atan2(y, x),
    "ceil": lambda r, x: float(math.ceil(x)),
    "cos": lambda r, x: math.cos(x),
    "degrees": lambda r, x: math.degrees(x),
    "dist": lambda r, a, b: math.dist(a, b),
    "exp": lambda r, x: math.exp(x),
    "floor": lambda r, x: float(math.floor(x)),
    "ln": lambda r, x: math.log(x),
    "log10": lambda r, x: math.log10(x),
    "log2": lambda r, x: math.log2(x),
    "pow": lambda r, x, y: float(x) ** y,
    "radians": lambda r, x: math.radians(x),
    "round": lambda r, x, places=0: float(round(x, int(places))),
    "sin": lambda r, x: math.sin(x),
    "sqrt": lambda r, x: math.sqrt(x),
    "tan": lambda r, x: math.tan(x),
    "vector": lambda r, x, y, z: vec((x, y, z)),
    "xsArrayCreateBool": lambda r, size=-1, value=False, name="": r.array_create("bool", size, value, name),
    "xsArrayCreateFloat": lambda r, size=-1, value=-1.0, name="": r.array_create("float", size, value, name),
    "xsArrayCreateInt": lambda r, size=-1, value=-1, name="": r.array_create("int", size, value, name),
    "xsArrayCreateString": lambda r, size=-1, value="", name="": r.array_create("string", size, value, name),
    "xsArrayCreateVector": lambda r, size=-1, value=(-1.0, -1.0, -1.0), name="": r.array_create("vector", size, value, name),
    "xsArrayGetBool": lambda r, a=-1, i=-1: r.array_get("bool", a, i),
    "xsArrayGetFloat": lambda r, a=-1, i=-1: r.array_get("float", a, i),
    "xsArrayGetInt": lambda r, a=-1, i=-1: r.array_get("int", a, i),
    "xsArrayGetSize": lambda r, a=-1: r.array_size(a),
    "xsArrayGetString": lambda r, a=-1, i=-1: r.array_get("string", a, i),
    "xsArrayGetVector": lambda r, a=-1, i=-1: r.array_get("vector", a, i),
    "xsArrayResizeBool": lambda r, a=-1, n=-1: r.array_resize("bool", a, n),
    "xsArrayResizeFloat": lambda r, a=-1, n=-1: r.array_resize("float", a, n),
    "xsArrayResizeInt": lambda r, a=-1, n=-1: r.array_resize("int", a, n),
    "xsArrayResizeString": lambda r, a=-1, n=-1: r.array_resize("string", a, n),
    "xsArrayResizeVector": lambda r, a=-1, n=-1: r.array_resize("vector", a, n),
    "xsArraySetBool": lambda r, a=-1, i=-1, v=False: r.array_set("bool", a, i, v),
    "xsArraySetFloat": lambda r, a=-1, i=-1, v=-1.0: r.array_set("float", a, i, v),
    "xsArraySetInt": lambda r, a=-1, i=-1, v=-1: r.array_set("int", a, i, v),
    "xsArraySetString": lambda r, a=-1, i=-1, v="": r.array_set("string", a, i, v),
    "xsArraySetVector": lambda r, a=-1, i=-1, v=(-1.0, -1.0, -1.0): r.array_set("vector", a, i, v),
    "xsBreakPoint": lambda r: None,
    "xsCeilToInt": lambda r, x: int32(math.ceil(x)),
    "xsChatData": lambda r, msg, value=-1: r.out(msg.replace("%d", str(int32(value)))),
    "xsDisableRule": lambda r, name: r.enable(name, False),
    "xsDisableRuleGroup": lambda r, group: r.enable_group(group, False),
    "xsDisableSelf": lambda r: r.enable(r.current, False),
    "xsDumpArrays": lambda r: r.dump_arrays(),
    "xsEnableRule": lambda r, name: r.enable(name, True),
    "xsEnableRuleGroup": lambda r, group: r.enable_group(group, True),
    "xsGetTime": lambda r: int32(r.now * 1000),
    "xsIsRuleEnabled": lambda r, name: bool(r.rules.get(name, {}).get("on")),
    "xsIsRuleGroupEnabled": lambda r, group: any(r.rules[n]["on"] for n in r.group(group)),
    "xsSetRuleMaxInterval": lambda r, name, s: r.set_rule(name, "maxInterval", s),
    "xsSetRuleMaxIntervalSelf": lambda r, s: r.set_rule(r.current, "maxInterval", s),
    "xsSetRuleMinInterval": lambda r, name, s: r.set_rule(name, "minInterval", s),
    "xsSetRuleMinIntervalSelf": lambda r, s: r.set_rule(r.current, "minInterval", s),
    "xsSetRulePriority": lambda r, name, p: r.set_rule(name, "priority", p),
    "xsSetRulePrioritySelf": lambda r, p: r.set_rule(r.current, "priority", p),
    "xsVectorGetX": lambda r, v: v[0],
    "xsVectorGetY": lambda r, v: v[1],
    "xsVectorGetZ": lambda r, v: v[2],
    "xsVectorLength": lambda r, v: math.sqrt(sum(c * c for c in v)),
    "xsVectorNormalize": lambda r, v: normalize(v),
    "xsVectorSet": lambda r, x, y, z: vec((x, y, z)),
    "xsVectorSetX": lambda r, v, x: vec((x, v[1], v[2])),
    "xsVectorSetY": lambda r, v, y: vec((v[0], y, v[2])),
    "xsVectorSetZ": lambda r, v, z: vec((v[0], v[1], z)),
}


def constants():
    """{name: [type, value, const]} of the built-in constants of the XS API (game/data/xs_constants.jsonl, #5807)."""
    import table
    return {r["name"]: [t, convert(t, tuple(v) if t == "vector" else v), True]
            for r in table.load("xs_constants.jsonl") for t, v in r.items() if t != "name"}


class Xs:
    """One XS script: its globals, functions and rules. load(name) gives the text of an include file; out(text) shows
    the text of xsChatData; host maps the names of game functions to callables (a later ticket of #5119)."""

    def __init__(self, text, load=None, out=print, host=None, steps=STEPS, path=None):
        self.load, self.out, self.host, self.max_steps = load, out, host or {}, steps
        self.globals, self.funcs, self.rules, self.statics = constants(), {}, {}, {}
        self.warned, self.included, self.started = set(), set(), False
        self.now, self.current, self.steps, self.scopes = 0.0, None, 0, []
        self.arrays = []                         # the xsArray functions: id -> [type, name, values]
        self.read(xs.parse(text, path))

    def read(self, nodes):
        for node in nodes:
            if node[0] == "include":
                if node[1] in self.included:
                    continue
                self.included.add(node[1])
                if self.load is None:
                    self.warn("include (no file loader)", node[1])
                else:
                    self.read(xs.parse(self.load(node[1]), node[1]))
            elif node[0] == "func":
                self.funcs[node[2]] = node
            elif node[0] == "rule":
                _, name, opts, block = node
                self.rules[name] = {"on": not opts.get("inactive"), "since": 0.0, "last": None, "body": block,
                                    "order": len(self.rules), **{k: opts.get(k) for k in xs.RULE_FLAGS | xs.RULE_VALUES}}
                self.rules[name]["priority"] = opts.get("priority", 0)
                self.rules[name]["minInterval"] = opts.get("minInterval", 1)
            else:
                _, typ, name, value, mods = node
                v = self.guard(f"variable {name}", lambda: self.eval(value) if value is not None else None)
                self.globals[name] = [typ, convert(typ, v), "const" in mods]

    def warn(self, what, name):
        if (what, name) not in self.warned:
            self.warned.add((what, name))
            print(f"XS script: unknown {what} {name}: skipped" if "error" not in what
                  else f"XS script: {what} in {name}: stopped", file=sys.stderr)

    # -- the arrays (xsArrayCreateInt, ...): a bad id or index gives one warning line and the default value

    def array(self, typ, a, i=None):
        """The values of array a of type typ, or None (one warning line)."""
        if not 0 <= a < len(self.arrays) or self.arrays[a][0] != typ:
            self.warn(f"{typ} array", a)
            return None
        values = self.arrays[a][2]
        if i is not None and not 0 <= i < len(values):
            self.warn(f"index of array {a}", i)
            return None
        return values

    def array_create(self, typ, size, value, name):
        if size < 0:
            self.warn("array size", size)
            return -1
        self.arrays.append([typ, name, [convert(typ, value)] * int(size)])
        return len(self.arrays) - 1

    def array_get(self, typ, a, i):
        values = self.array(typ, a, i)
        return DEFAULT[typ] if values is None else values[i]

    def array_set(self, typ, a, i, v):
        values = self.array(typ, a, i)
        if values is None:
            return False
        values[i] = convert(typ, v)
        return True

    def array_resize(self, typ, a, n):
        values = self.array(typ, a)
        if values is None or n < 0:
            return False
        values[:] = values[:n] + [DEFAULT[typ]] * (n - len(values))
        return True

    def array_size(self, a):
        if not 0 <= a < len(self.arrays):
            self.warn("array", a)
            return -1
        return len(self.arrays[a][2])

    def dump_arrays(self):
        for a, (typ, name, values) in enumerate(self.arrays):
            self.out(f"Array {a} {name} ({typ}, {len(values)}): " + ", ".join(text(v) for v in values))

    # -- the calls of the game program

    def tick(self, now):
        """Run main() at the first tick, then each due rule (a higher priority first, then the order of the script)."""
        self.now = float(now)
        if not self.started:
            self.started = True
            for r in self.rules.values():
                r["since"] = self.now
            if "main" in self.funcs:
                self.call("main")
        done = set()
        while True:                              # a rule that a rule of this tick enables can run in this tick
            due = [n for n, r in self.rules.items() if n not in done and r["on"] and self.due(r)]
            if not due:
                break
            name = min(due, key=lambda n: (-self.rules[n]["priority"], self.rules[n]["order"]))
            r = self.rules[name]
            done.add(name)
            r["last"], self.current = self.now, name
            self.guard(f"rule {name}", lambda: self.run_body(r["body"]))
            self.current = None

    def due(self, r):
        if r["highFrequency"]:
            return True
        if r["last"] is None:
            return self.now >= r["since"] + (0 if r["runImmediately"] else r["minInterval"])
        gap = r["minInterval"] if r["maxInterval"] is None else min(r["minInterval"], r["maxInterval"])
        return self.now >= r["last"] + gap

    def call(self, name, *args):
        """Call a function of the script (main, a Script Call): its return value, or None after an error."""
        return self.guard(f"function {name}", lambda: self.invoke(name, list(args)))

    def get(self, name):
        return self.globals[name][1] if name in self.globals else None

    def guard(self, where, fn):
        self.steps = 0
        try:
            return fn()
        except Flow:
            return None
        except (XsRunError, ArithmeticError, TypeError, ValueError, IndexError, RecursionError) as e:
            self.warn(f"runtime error ({e})", where)
            return None

    # -- the rule functions

    def enable(self, name, on):
        r = self.rules.get(name)
        if r is None:
            return self.warn("rule", name)
        if on and not r["on"]:
            r["since"], r["last"] = self.now, None
        r["on"] = on

    def enable_group(self, group, on):
        for name in self.group(group):
            self.enable(name, on)

    def group(self, group):
        return [n for n, r in self.rules.items() if r["group"] == group]

    def set_rule(self, name, key, value):
        if name not in self.rules:
            return self.warn("rule", name)
        self.rules[name][key] = value

    # -- the tree

    def step(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise XsRunError(f"step limit {self.max_steps}")

    def lookup(self, name):
        for scope in reversed(self.scopes[-1] if self.scopes else []):
            if name in scope:
                return scope[name]
        return self.globals.get(name)

    def invoke(self, name, args):
        if name in self.funcs:
            _, typ, _, params, block, _ = self.funcs[name]
            if len(args) > len(params):
                raise XsRunError(f"{name}: too many arguments")
            frame = {}
            for i, (ptype, pname, default) in enumerate(params):
                v = args[i] if i < len(args) else (self.eval(default) if default is not None else None)
                frame[pname] = [ptype, convert(ptype, v), False]
            self.scopes.append([frame])
            try:
                self.run_body(block, name)
                value = None
            except Flow as f:
                if f.kind != "return":
                    raise XsRunError(f"{f.kind} outside a loop")
                value = f.value
            finally:
                self.scopes.pop()
            return convert(typ, value)
        fn = self.host.get(name) or BUILTIN.get(name)
        if fn is None:
            self.warn("function", name)
            return 0
        return fn(*args) if name in self.host else fn(self, *args)

    def run_body(self, block, func=None):
        if func is None:
            self.scopes.append([{}])
            try:
                self.exec(block, func)
            finally:
                self.scopes.pop()
        else:
            self.exec(block, func)

    def exec(self, node, func=None):
        self.step()
        k = node[0]
        if k == "block":
            self.scopes[-1].append({})
            try:
                for s in node[1]:
                    self.exec(s, func)
            finally:
                self.scopes[-1].pop()
        elif k == "var":
            _, typ, name, value, mods = node
            if "static" in mods:                 # a static local keeps its value between the calls
                key = (func or self.current, name)
                if key not in self.statics:
                    self.statics[key] = [typ, convert(typ, self.eval(value) if value is not None else None), False]
                self.scopes[-1][-1][name] = self.statics[key]
            else:
                v = self.eval(value) if value is not None else None
                self.scopes[-1][-1][name] = [typ, convert(typ, v), "const" in mods]
        elif k == "expr":
            self.eval(node[1])
        elif k == "if":
            if self.eval(node[1]):
                self.exec(node[2], func)
            elif node[3] is not None:
                self.exec(node[3], func)
        elif k == "while":
            while self.eval(node[1]):
                self.step()
                if self.loop_body(node[2], func):
                    break
        elif k == "for":
            _, var, start, op, limit, body = node
            if self.lookup(var) is None:
                self.scopes[-1][-1][var] = ["int", 0, False]
            self.assign(var, self.eval(start))
            while binary(op, self.lookup(var)[1], self.eval(limit)):
                self.step()
                if self.loop_body(body, func):
                    break
                self.assign(var, self.lookup(var)[1] + (1 if op in ("<", "<=") else -1))
        elif k == "switch":
            value = self.eval(node[1])
            cases = node[2]
            hit = next((b for label, b in cases if label is not None and self.eval(label) == value), None)
            if hit is None:
                hit = next((b for label, b in cases if label is None), [])
            try:
                for s in hit:                    # no fall through to the next case
                    self.exec(s, func)
            except Flow as f:
                if f.kind != "break":
                    raise
        elif k in ("break", "continue"):
            raise Flow(k)
        elif k == "return":
            raise Flow("return", self.eval(node[1]) if node[1] is not None else None)
        else:
            raise XsRunError(f"unknown statement {k}")

    def loop_body(self, body, func):
        """Run one turn of a loop; True on break."""
        try:
            self.exec(body, func)
        except Flow as f:
            if f.kind == "break":
                return True
            if f.kind != "continue":
                raise
        return False

    def assign(self, name, value):
        slot = self.lookup(name)
        if slot is None:
            self.warn("variable", name)
            return value
        if slot[2]:
            raise XsRunError(f"assignment to the constant {name}")
        slot[1] = convert(slot[0], value)
        return slot[1]

    def eval(self, node):
        k = node[0]
        if k in ("num", "str", "bool"):
            return node[1]
        if k == "name":
            slot = self.lookup(node[1])
            if slot is None:
                self.warn("variable", node[1])
                return 0
            return slot[1]
        if k == "assign":
            return self.assign(node[1], self.eval(node[2]))
        if k == "call":
            return self.invoke(node[1], [self.eval(a) for a in node[2]])
        if k == "bin":
            _, op, a, b = node
            if op == "&&":
                return bool(self.eval(a)) and bool(self.eval(b))
            if op == "||":
                return bool(self.eval(a)) or bool(self.eval(b))
            return binary(op, self.eval(a), self.eval(b))
        if k == "unary":
            _, op, a = node
            if op in ("++", "--"):
                return self.assign(self.target(a), self.eval(a) + (1 if op == "++" else -1))
            v = self.eval(a)
            if op == "!":
                return not v
            return tuple(-c for c in v) if isinstance(v, tuple) else -v
        if k == "post":
            _, op, a = node
            old = self.eval(a)
            self.assign(self.target(a), old + (1 if op == "++" else -1))
            return old
        raise XsRunError(f"unknown expression {k}")

    @staticmethod
    def target(node):
        if node[0] != "name":
            raise XsRunError("++ and -- need a variable")
        return node[1]
