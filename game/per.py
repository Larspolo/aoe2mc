"""AoE2 AI scripts (`.per` files, epic #4526): parse() reads the text into rules, as the AI compiler of the game does
(#4527). A later step runs the rules on a bot (game/bot.py).

The language (AoE2 AI Scripting Encyclopedia, https://airef.github.io, "Syntax"):
    ; a comment to the end of the line
    (defconst NAME VALUE)                     a name for a number; a later rule gets the number
    (defrule FACT ... => ACTION ...)          the actions run when all facts are true
    (load "FOLDER\\FILE")                     the rules of another file of the AI folder (".per" added)
    #load-if-defined SYMBOL ... #else ... #end-if   keep the text by the symbols of the game (also -not-defined)
A fact is (NAME ARG ...), or (and F F ...), (or F F ...), (nand F F ...), (nor F F ...), (not F). The relational
operators also have words (less-than ...): the rules get the symbols of REL. The game reads the names in any case: the
rules get lower case names (a text in double quotes keeps its case, as a Text). The parser knows the syntax only, not
the names of the facts and actions: the step that runs the rules warns of an unknown name.

Script(rules, bot).step() runs the rules on a bot (#4528): in one pass, the actions of each rule that is not disabled
and whose facts are all true, in the order of the file, as AoE2 does. The facts read the gather.Gather of the bot and
the actions use its paths (train.queue, build.found). The script names of units, buildings, technologies and ages map
to the names of the game program by game/data/per_names.jsonl (NAMES). An unknown fact, action or name gives one
warning line and counts as false (a fact) or does nothing (an action).
"""
import collections
import json
import operator
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

Rule = collections.namedtuple("Rule", "facts actions file line")   # facts: (name, *args) or (logic, *facts)
LOGIC = {"and", "nand", "nor", "not", "or"}
REL = {"<": "<", "<=": "<=", ">": ">", ">=": ">=", "==": "==", "!=": "!=", "less-than": "<", "less-or-equal": "<=",
       "greater-than": ">", "greater-or-equal": ">=", "equal": "==", "not-equal": "!="}
TOKEN = re.compile(r'(;[^\n]*)|"([^"\n]*)"|([()])|(#[\w-]+)|([^\s()";]+)|(\n)|(\S)')


class Text(str):
    """A text in double quotes (chat-to-all "..."): no constant, no lower case."""


def tokens(text, file, defined):
    """(token, line) of the text with no comments, and only the parts that the # directives keep. A Text is a string."""
    line, keep, words = 1, [], iter(TOKEN.finditer(text))
    for m in words:
        comment, string, paren, directive, atom, newline, bad = m.groups()
        if newline:
            line += 1
        elif bad:
            raise ValueError(f"{file}:{line}: a text with no end quote")
        elif directive:
            d = directive.lower()
            if d in ("#load-if-defined", "#load-if-not-defined"):
                symbol = next(words, None)                               # the next token: on the same line
                if symbol is None or not symbol[5]:
                    raise ValueError(f"{file}:{line}: {d} needs a symbol")
                keep.append((symbol[5].lower() in defined) == (d == "#load-if-defined"))
            elif d == "#else" and keep:
                keep[-1] = not keep[-1]
            elif d == "#end-if" and keep:
                keep.pop()
            else:
                raise ValueError(f"{file}:{line}: {directive} with no #load-if-defined" if d in ("#else", "#end-if")
                                 else f"{file}:{line}: unknown directive {directive}")
        elif not comment and all(keep):
            yield (Text(string) if string is not None else paren or atom), line
    if keep:
        raise ValueError(f"{file}: #load-if-defined with no #end-if")


def forms(text, file, defined):
    """The top-level forms of the text: nested lists of (atom, line), each list with its line first."""
    stack = [[0]]
    for t, line in tokens(text, file, defined):
        if t == "(" and not isinstance(t, Text):
            stack.append([line])
        elif t == ")" and not isinstance(t, Text):
            if len(stack) == 1:
                raise ValueError(f"{file}:{line}: a ) with no (")
            done = stack.pop()
            stack[-1].append(done)
        elif len(stack) == 1:
            raise ValueError(f"{file}:{line}: {t} outside a form")
        else:
            stack[-1].append((t, line))
    if len(stack) > 1:
        raise ValueError(f"{file}:{stack[-1][0]}: a ( with no )")
    return stack[0][1:]


def value(atom, consts):
    """A number, a Text, or a lower case symbol (the value of a constant)."""
    if isinstance(atom, Text):
        return atom
    if re.fullmatch(r"[+-]?\d+", atom):
        return int(atom)
    return consts.get(atom.lower(), atom.lower())


def name_of(form, file):
    """The name of a form (fact, action, defrule ...)."""
    if len(form) < 2 or isinstance(form[1], list) or isinstance(form[1][0], Text):
        raise ValueError(f"{file}:{form[0]}: a form with no name")
    return form[1][0].lower()


def fact(form, file, consts):
    """(name, *args) of a fact; (logic, *facts) of and, or, nand, nor, not."""
    if not isinstance(form, list):
        raise ValueError(f"{file}:{form[1]}: {form[0]} is not a fact in ( )")
    name, args = name_of(form, file), form[2:]
    if name in LOGIC:
        if len(args) != 1 if name == "not" else len(args) < 2:
            raise ValueError(f"{file}:{form[0]}: {name} with {len(args)} facts")
        return (name, *(fact(a, file, consts) for a in args))
    if any(isinstance(a, list) for a in args):
        raise ValueError(f"{file}:{form[0]}: a fact in the fact {name}")
    return (name, *(REL.get(v, v) if isinstance(v := value(a, consts), str) and not isinstance(v, Text) else v
                    for a, _ in args))


def action(form, file, consts):
    """(name, *args) of an action."""
    if not isinstance(form, list) or any(isinstance(a, list) for a in form[2:]):
        raise ValueError(f"{file}:{form[0] if isinstance(form, list) else form[1]}: an action must be (NAME ARG ...)")
    return (name_of(form, file), *(value(a, consts) for a, _ in form[2:]))


def find(folder, name):
    """The path of (load "NAME") in the AI folder: ".per" added, backslashes as folders, and any case, as on Windows."""
    path = folder or ""
    parts = [p for p in name.replace("\\", "/").split("/") if p]
    for k, part in enumerate(parts):
        part += "" if k < len(parts) - 1 or os.path.splitext(part)[1] else ".per"
        here = os.listdir(path) if os.path.isdir(path) else []
        path = os.path.join(path, next((f for f in sorted(here) if f.lower() == part.lower()), part))
    return path


def parse(text, defined=(), folder=None, file="<script>", consts=None, depth=0):
    """The rules of the text, in the order of the file. defined: the symbols of the game for #load-if-defined (for
    example the age, the map type, the civilization). folder: the AI folder of (load ...). A broken text gives a
    ValueError with the file and the line; an unknown top-level form gives one warning line and is skipped."""
    defined = {s.lower() for s in defined}
    consts = {} if consts is None else consts           # one table for the file and the files that it loads
    rules = []
    for form in forms(text, file, defined):
        if not isinstance(form, list):
            raise ValueError(f"{file}:{form[1]}: {form[0]} outside a form")
        name, line, args = name_of(form, file), form[0], form[2:]
        if name == "defrule":
            atoms = [a[0] if isinstance(a, tuple) else None for a in args]
            if "=>" not in atoms:
                raise ValueError(f"{file}:{line}: defrule with no =>")
            k = atoms.index("=>")
            if not k or k == len(args) - 1:
                raise ValueError(f"{file}:{line}: defrule needs a fact and an action")
            rules.append(Rule(tuple(fact(f, file, consts) for f in args[:k]),
                              tuple(action(a, file, consts) for a in args[k + 1:]), file, line))
        elif name == "defconst":
            if len(args) != 2 or isinstance(args[0], list) or isinstance(args[1], list) or \
                    not isinstance(v := value(args[1][0], consts), int):
                raise ValueError(f"{file}:{line}: defconst must be (defconst NAME NUMBER)")
            if (key := args[0][0].lower()) in consts:
                raise ValueError(f"{file}:{line}: defconst {key} again")   # the game does not allow it
            consts[key] = v
        elif name == "load":
            if len(args) != 1 or not isinstance(args[0], tuple) or not isinstance(args[0][0], Text):
                raise ValueError(f'{file}:{line}: load must be (load "FILE")')
            path = find(folder, args[0][0])
            if folder is None or not os.path.isfile(path) or depth > 20:
                raise ValueError(f"{file}:{line}: no file {path} for load" if depth <= 20 else
                                 f"{file}:{line}: load loops")
            with open(path, encoding="utf-8", errors="replace") as f:
                rules += parse(f.read(), defined, folder, path, consts, depth + 1)
        else:
            print(f"AI script {file}:{line}: unknown form {name}: skipped", file=sys.stderr)
    return rules


def read(path, defined=()):
    """The rules of a .per file; its folder is the AI folder of (load ...)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse(f.read(), defined, os.path.dirname(os.path.abspath(path)), path)


NAMES = {}                                                         # script name -> its line of per_names.jsonl
OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq, "!=": operator.ne}
STOCK = ("food", "wood", "gold", "stone")


def names():
    """NAMES, read once: game/per.py also runs with no game data (the parser of #4527)."""
    if not NAMES:
        import table
        NAMES.update((r["name"], r) for r in table.load("per_names.jsonl"))
    return NAMES


class Script:
    """The rules of an AI script on a bot.Bot: goals and timers keep their values between steps."""

    def __init__(self, rules, bot):
        self.rules, self.bot = list(rules), bot
        self.off = set()                                           # the rules after disable-self
        self.goals, self.timers = {}, {}                           # goal id -> value; timer id -> AoE2 second due
        self.warned = set()

    def warn(self, what, name):
        if (what, name) not in self.warned:
            self.warned.add((what, name))
            print(f"AI script: unknown {what} {name}: skipped", file=sys.stderr)

    def game(self, name, *kinds):
        """The name of the game program of a script name of one of kinds, or None (one warning)."""
        row = names().get(name)
        if row is None or row["kind"] not in kinds:
            return self.warn(" or ".join(kinds), name)
        return row.get("game")

    def step(self):
        """Check the facts of each rule that is not disabled and run the actions of each rule whose facts are true."""
        for k, rule in enumerate(self.rules):
            if k not in self.off and all(self.check(f) for f in rule.facts):
                for a in rule.actions:
                    self.act(k, a)

    def check(self, f):
        name, args = f[0], f[1:]
        if name in LOGIC:
            got = [self.check(a) for a in args]
            return {"and": all(got), "or": any(got), "nand": not all(got), "nor": not any(got), "not": not got[0]}[name]
        if name == "goal":                                         # (goal ID VALUE) or (goal ID REL VALUE)
            op, v = ("==", args[1]) if len(args) == 2 else args[1:3]
            return OPS[op](self.goals.get(args[0], -1), v)
        if name == "timer-triggered":
            return args[0] in self.timers and self.bot.time >= self.timers[args[0]]
        if name in ("true", "false"):
            return name == "true"
        if name in ("can-train", "can-build", "can-research", "research-completed"):
            return self.can(name, args[0])
        if name in ("unit-type-count", "building-type-count"):
            if (n := self.game(args[0], "unit" if name[0] == "u" else "building")) is None:
                return False
            return OPS[args[1]](self.count(n), args[2])
        if name == "current-age":
            row = names().get(args[1])
            if row is None or row["kind"] != "age":
                return self.warn("age", args[1]) or False
            import build
            return OPS[args[0]](build.ages(self.bot.g), row["age"])
        value = self.value(name)
        if value is None:
            return self.warn("fact", name) or False
        return OPS[args[0]](value, args[1])

    def value(self, name):
        """The number of a fact (REL VALUE), or None for an unknown fact."""
        import train
        g, b = self.bot.g, self.bot
        if name.endswith("-amount") and (res := name.removesuffix("-amount")) in STOCK:
            return g.stock[res]
        return {"game-time": lambda: b.time, "population": lambda: g.pop,
                "civilian-population": lambda: len(g.villagers), "military-population": lambda: len(g.soldiers),
                "housing-headroom": lambda: max(train.limit(g) - g.pop, 0),
                "population-headroom": lambda: max(train.max_pop(g) - g.pop, 0)}.get(name, lambda: None)()

    def count(self, n):
        """The own live units or complete buildings of game name n."""
        import train
        g = self.bot.g
        if n.startswith("VILLAGER"):
            return len(g.villagers)
        return sum(u == n for u in g.soldiers.values()) + train.owned(g).count(n)

    def paid(self, cost):
        return all(self.bot.g.stock[r] >= v for r, v in cost.items())

    def homes(self, n):
        """The block cells of the own buildings that offer n now."""
        import build
        import train
        g = self.bot.g
        if build.locked(g, n):
            return []
        return [(rect[0], rect[2]) for rect, home in sorted(train.homes(g).items()) if n in train.trains(g, home)]

    def can(self, name, arg):
        import build
        import train
        g = self.bot.g
        if name == "can-build":
            n = self.game(arg, "building")
            return bool(n and g.villagers and not build.locked(g, n) and self.paid(build.price(g, n)))
        n = self.game(arg, "unit") if name == "can-train" else self.game(arg, "tech", "age")
        if n is None:
            return False
        if name == "research-completed":
            return train.researched(g, n)
        if name == "can-research" and (train.researched(g, n) or train.queued(g, n)):
            return False
        if name == "can-train" and g.pop >= train.limit(g):
            return False
        return bool(self.homes(n)) and self.paid(train.price(g, n))

    def act(self, k, a):
        import build
        import train
        name, args, b = a[0], a[1:], self.bot
        g = b.g
        if name in ("train", "research"):
            n = self.game(args[0], "unit") if name == "train" else self.game(args[0], "tech", "age")
            if n and self.can("can-" + name, args[0]):
                next((c for c in self.homes(n) if train.queue(g, b.nobody, c, n)), None)
        elif name == "build":
            n = self.game(args[0], "building")
            if n and self.can("can-build", args[0]) and (center := b.center()) \
                    and (rect := build.near(g, n, center)) is not None:
                b.builder(build.found(g, n, rect))
        elif name == "disable-self":
            self.off.add(k)
        elif name == "set-goal":
            self.goals[args[0]] = args[1]
        elif name == "enable-timer":
            self.timers[args[0]] = b.time + args[1]
        elif name == "disable-timer":
            self.timers.pop(args[0], None)
        elif name == "chat-to-all":
            g.command("tellraw @a " + json.dumps({"text": f"<Player {g.player}> {args[0]}"}))
        elif name != "do-nothing":
            self.warn("action", name)
