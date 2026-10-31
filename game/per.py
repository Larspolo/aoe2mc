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
import math
import operator
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

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
MATH = ("=", "+", "-", "*", "/", "z/", "mod", "min", "max", "neg", "%*", "%/")   # airef "mathOp" (up-modify-*)
RULE_CHECKS = 10000                     # the rule checks of one pass: a loop with no end stops there (airef RuleDelta)
GET_FACT = ("up-get-fact", "up-get-fact-max", "up-get-fact-min", "up-get-fact-sum", "up-get-player-fact")
STOCK = ("food", "wood", "gold", "stone")
TOWN = 30                       # tiles around the own town center: "in town" (AoE2 sn-maximum-town-size, airef "Facts")
PERIMETERS = {1: (10, 20), 2: (18, 30)}   # tiles from the town center to each wall ring (airef "build-wall", #4740)
OCTAGON = math.tan(math.pi / 8)           # half the straight side of a regular octagon per its radius


def names():
    """NAMES, read once: game/per.py also runs with no game data (the parser of #4527)."""
    if not NAMES:
        import table
        NAMES.update((r["name"], r) for r in table.load("per_names.jsonl"))
    return NAMES


# The strategic numbers of AoE2 DE with their defaults and ids (airef "Strategic numbers", #4685): only the gatherer
# percentages and the attack group sizes change the bot (Script.number); the others keep their value for the script.
SN = {r["name"]: r["default"] for r in table.load("per_numbers.jsonl")}
SN_IDS = {r["id"]: r["name"] for r in table.load("per_numbers.jsonl")}   # a script can name a number by its id


SETUP = ("civ-selected", "death-match-game", "difficulty", "map-size", "map-type", "regicide-game", "starting-age")


def map_size(data):
    """The airef map size of a map (aoe2mc.json): the smallest size with at least its tiles, else the largest."""
    n = len(data.get("ground", ())) // data.get("tile_size", 1)
    sizes = sorted((r["tiles"], k) for k, r in names().items() if r["kind"] == "map-size")
    return next((k for t, k in sizes if t >= n), sizes[-1][1])


def symbols(data, player, difficulty, modes=(), age="dark"):
    """The system symbols of #load-if-defined (airef "Conditional loading") of the bot of player: the civilization
    (BRITONS-CIV), the difficulty (DIFFICULTY-HARD), the game types (DEATH-MATCH, REGICIDE), the start age
    (CASTLE-AGE-START), the map type (SCENARIO-MAP) and the map size (TINY-MAP). A map that the game program knows by
    no airef name is SCENARIO-MAP."""
    civ = data.get("players", {}).get(str(player), {}).get("civ")
    out = {f"{k}-civ" for k, r in names().items() if r["kind"] == "civ" and r["game"] == civ}
    out |= {f"difficulty-{k}" for k, r in names().items() if r["kind"] == "difficulty" and r["game"] == difficulty}
    return out | set(modes) | {f"{age}-age-start", "scenario-map", map_size(data)}


class Script:
    """The rules of an AI script on a bot.Bot: goals and timers keep their values between steps."""

    def __init__(self, rules, bot):
        self.rules, self.bot = list(rules), bot
        self.off = set()                                           # the rules after disable-self
        self.goals, self.timers = {}, {}                           # goal id -> value; timer id -> AoE2 second due
        self.aged = {}                                             # player -> (ages, AoE2 second of the last age up)
        self.warned = set()
        self.sn = {}                                               # strategic number name -> value (#4530)
        self.attacking = False                                     # attack-now ran: the bot may attack
        self.escrow, self.pct = {}, {}                             # resource -> escrow; -> escrow percentage (#4682)
        self.last = None                                           # the stock after the last step: new income
        self.rings = {}                                            # perimeter -> the sides of its wall ring (ring())
        self.heard, self.read = set(), {}                          # (player, taunt) not acknowledged; player -> read
        self.jump = None                                           # the rule after the actions of this rule (up-jump-*)

    def number(self, name):
        return self.sn.get(name, SN[name])

    def percent(self):
        """The shares of the four gatherer percentages (in percent of the villagers), or None when the script set none."""
        pct = {r: max(self.number(f"sn-{r}-gatherer-percentage"), 0) for r in ("food", "wood", "gold", "stone")}
        total = sum(pct.values())
        return {r: v / total for r, v in pct.items()} if total else None

    def warn(self, what, name):
        if (what, name) not in self.warned:
            self.warned.add((what, name))
            print(f"AI script: unknown {what} {name}: skipped", file=sys.stderr)

    def operand(self, kind, ref):
        """The value of ref for a typed prefix: a constant ("" or c:), a goal (g:) or a strategic number (s:, by name or
        id). None, with one warning, for an unknown goal or number."""
        if kind == "g":
            if ref not in self.goals:
                return self.warn("goal", ref)
            return self.goals[ref]
        if kind == "s":
            ref = SN_IDS.get(ref, ref)
            if ref not in SN:
                return self.warn("strategic number", ref)
            return self.number(ref)
        return ref

    def compare(self, op, value, ref):
        """value REL ref; a typed operator (airef "Typed operators") reads ref as a constant (c:), the value of a
        strategic number (s:) or of a goal (g:). An unknown operator, number or goal gives one warning and is false."""
        kind, _, rel = op.rpartition(":")
        if rel not in OPS or kind not in ("", "c", "s", "g"):
            return self.warn("operator", op) or False
        ref = self.operand(kind, ref)
        return False if ref is None else OPS[rel](value, ref)

    def math(self, op, value, ref):
        """The new value of value OP ref (airef "mathOp", up-modify-*). None, with one warning, for an unknown operator
        or number: the command does nothing. / and mod by 0 keep the value; /, z/, mod, %* and %/ are whole numbers,
        a half away from 0 for / and truncated toward 0 for the others (7 / 2 = 4, 7 z/ 2 = 3)."""
        kind, _, rel = op.rpartition(":")
        if rel not in MATH or kind not in ("", "c", "s", "g"):
            return self.warn("operator", op)
        ref = self.operand(kind, ref)
        if ref is None:
            return None
        sign = 1 if (value < 0) == (ref < 0) else -1                  # the sign of value / ref
        if rel == "=":
            return ref
        if rel == "+":
            return value + ref
        if rel == "-":
            return value - ref
        if rel == "*":
            return value * ref
        if rel == "min":
            return min(value, ref)
        if rel == "max":
            return max(value, ref)
        if rel == "neg":
            return -ref
        if rel == "%*":
            return sign * (abs(value * ref) // 100)
        if not ref:
            return value
        if rel == "/":
            return sign * ((2 * abs(value) + abs(ref)) // (2 * abs(ref)))
        if rel == "z/":
            return sign * (abs(value) // abs(ref))
        if rel == "mod":                                               # the sign of value, as in C
            return (1 if value >= 0 else -1) * (abs(value) % abs(ref))
        return sign * (abs(value * 100) // abs(ref))                   # %/

    def jump_to(self, kind, ref):
        """The rule number of a jump (up-jump-direct, up-jump-dynamic): operand(kind, ref), or None with one warning for
        an unknown kind."""
        kind = kind.rstrip(":")
        if kind not in ("", "c", "g", "s"):
            return self.warn("operator", kind)
        return self.operand(kind, ref)

    def game(self, name, *kinds):
        """The name of the game program of a script name of one of kinds, or None (one warning)."""
        row = names().get(name)
        if row is None or row["kind"] not in kinds:
            return self.warn(" or ".join(kinds), name)
        if "set" in row:                                    # a set or class: count() sums its units (#4681)
            return tuple(row["set"])
        if "civ" in row:                                    # the unique unit or technology of the civilization (#4681)
            return self.unique(row["civ"]) or self.warn(" or ".join(kinds), name)
        return row.get("game")

    def unique(self, part):
        """The unique unit ("unit"), its elite unit ("elite"), its elite upgrade ("upgrade") or the Castle Age unique
        technology ("research") of the civilization of the bot, or None."""
        import civs
        import train
        civ = civs.real(self.bot.g)
        u = civs.UNIQUE.get(civ)
        names = {r["name"] for r in train.ROWS}
        n = {"unit": u, "elite": u and f"ELITE_{u}", "upgrade": u and f"ELITE_{u}_UPGRADE",
             "research": next((r["name"] for r in train.ROWS if r.get("civ") == civ and r.get("age") == 2), None)}[part]
        return n if n in names else None

    def step(self):
        """Check the facts of each rule that is not disabled and run the actions of each rule whose facts are true. A jump
        (up-jump-*) goes to another rule of the pass; a pass of more than RULE_CHECKS checks stops (a loop with no end)."""
        self.income()
        self.hear()
        k, checks = 0, 0
        while 0 <= k < len(self.rules):
            checks += 1
            if checks > RULE_CHECKS:
                if ("rule loop", "") not in self.warned:
                    self.warned.add(("rule loop", ""))
                    print(f"AI script: a loop of rules has no end: the pass stops after {RULE_CHECKS} checks", file=sys.stderr)
                break
            rule = self.rules[k]
            self.jump = k + 1
            if k not in self.off and all(self.check(f) for f in rule.facts):
                for a in rule.actions:
                    self.act(k, a)
            k = self.jump
        self.last = dict(self.bot.g.stock)

    def income(self):
        """Put the escrow percentage of each new income (the growth of the stock since the last step) into escrow; the
        escrow is never more than the stock."""
        stock = self.bot.g.stock
        for r in STOCK:
            new = stock[r] - (self.last or stock).get(r, stock[r])
            e = self.escrow.get(r, 0) + (new * self.pct.get(r, 0) // 100 if new > 0 else 0)
            if e := min(e, stock[r]):
                self.escrow[r] = e
            else:
                self.escrow.pop(r, None)

    def hear(self):
        """Keep the new taunts of each player (gather.Gather.taunted, #4827) until acknowledge-taunt, as AoE2 does."""
        import build
        for x in {id(x): x for x in [*build.sides(self.bot.g), self.bot.g]}.values():
            log = getattr(x, "taunted", [])
            self.heard.update((x.player, int(n)) for n in log[self.read.get(x.player, 0):])
            self.read[x.player] = len(log)

    def check(self, f):
        name, args = f[0], f[1:]
        if name in LOGIC:
            got = [self.check(a) for a in args]
            return {"and": all(got), "or": any(got), "nand": not all(got), "nor": not any(got), "not": not got[0]}[name]
        if name == "goal":                                         # (goal ID VALUE) or (goal ID REL VALUE)
            op, v = ("==", args[1]) if len(args) == 2 else args[1:3]
            return self.compare(op, self.goals.get(args[0], -1), v)
        if name in GET_FACT:                                       # a command as a fact: it runs, and is true
            self.get_fact(name, args)
            return True
        if name in ("up-modify-goal", "up-modify-sn"):             # a command as a fact: it runs, and is true
            self.act(None, (name, *args))
            return True
        if name == "up-compare-goal":                              # (up-compare-goal GOAL REL VALUE)
            return self.compare(args[1], self.goals.get(args[0], -1), args[2])
        if name == "up-compare-sn":                                # (up-compare-sn SN REL VALUE)
            sn = SN_IDS.get(args[0], args[0])
            if sn not in SN:
                return self.warn("strategic number", sn) or False
            return self.compare(args[1], self.number(sn), args[2])
        if name == "up-compare-const":                             # (up-compare-const CONST REL VALUE)
            return self.compare(args[1], args[0], args[2])
        if name == "strategic-number":                             # (strategic-number NAME REL VALUE)
            args = (SN_IDS.get(args[0], args[0]),) + tuple(args[1:])
            if args[0] not in SN:
                return self.warn("strategic number", args[0]) or False
            return self.compare(args[1], self.sn.get(args[0], SN[args[0]]), args[2])
        if name == "timer-triggered":
            return args[0] in self.timers and self.bot.time >= self.timers[args[0]]
        if name in ("true", "false"):
            return name == "true"
        if name == "stance-toward":                                # (stance-toward PLAYER STANCE)
            import diplomacy
            return diplomacy.stance(self.bot.g, args[0]) == args[1]
        if name in ("can-train", "can-build", "can-research", "research-available", "research-completed"):
            return self.can(name, args[0])
        if name in ("can-train-with-escrow", "can-build-with-escrow", "can-research-with-escrow"):
            return self.can(name.removesuffix("-with-escrow"), args[0], True)
        if name in ("unit-type-count", "building-type-count", "unit-type-count-total", "building-type-count-total"):
            if (n := self.game(args[0], "unit" if name[0] == "u" else "building")) is None:
                return False
            return self.compare(args[1], self.count(n, total=name.endswith("-total")), args[2])
        if name in ("can-buy-commodity", "can-sell-commodity"):
            return self.trade_ok(name == "can-buy-commodity", args[0])
        if name in ("commodity-buying-price", "commodity-selling-price"):
            import market
            if args[0] not in market.RATES:
                return self.warn("commodity", args[0]) or False
            return self.compare(args[1], market.price(self.bot.g, args[0], name == "commodity-buying-price"), args[2])
        if name in ("resource-found", "dropsite-min-distance"):       # (dropsite-min-distance RESOURCE REL VALUE)
            if args[0] in ("live-boar", "dead-boar"):                  # the game program has no hunt for bots yet
                return name != "resource-found" and self.compare(args[1], 255, args[2])
            if args[0] not in STOCK:
                return self.warn("resource", args[0]) or False
            if name == "resource-found":                               # no fog for bots: each source counts
                return any(k > 0 for k in self.bot.sources(args[0]).values())
            return self.compare(args[1], self.drop_distance(args[0]), args[2])
        if name == "sheep-and-forage-too-far":
            return self.forage_far()
        if name == "escrow-amount":                                # (escrow-amount RESOURCE REL VALUE)
            return self.compare(args[1], self.escrow.get(args[0], 0), args[2])
        if name == "current-age":
            return self.age(self.bot.g, *args)
        if name == "current-age-time":
            return self.compare(args[0], self.age_time(self.bot.g), args[1])
        if name == "taunt-detected":                               # (taunt-detected PLAYER TAUNT)
            return (args[0], args[1]) in self.heard
        if name == "players-taunt-detected":                       # (players-taunt-detected PLAYER-TYPE TAUNT)
            xs, every = self.sides(args[0])
            got = [(x.player, args[1]) in self.heard for x in xs]
            return bool(got) and (all(got) if every else any(got))
        if name == "wall-completed-percentage":                    # (wall-completed-percentage PERIMETER REL VALUE)
            return self.ring(args[0]) is not None and self.compare(args[1], self.walled(args[0]), args[2])
        if name == "enemy-buildings-in-town":
            return self.in_town()
        if name in SETUP:
            return self.setup(name, args)
        if name.startswith("players-"):                            # (players-FACT PLAYER ...): the other players
            return self.players(name.removeprefix("players-"), args[0], args[1:])
        value = self.value(name)
        if value is None:
            return self.warn("fact", name) or False
        return self.compare(args[0], value, args[1])

    def setup(self, name, args):
        """A fact of the game setup (airef "Facts"): the civilization, the difficulty, the game type, the start age
        and the map."""
        import bot as bots
        import civs
        import gather
        g = self.bot.g
        if name == "civ-selected":
            return (civ := self.game(args[0], "civ")) is not None and civs.real(g) == civ
        if name in ("death-match-game", "regicide-game"):
            return gather.has_mode(g, name.removesuffix("-game"))
        if name == "difficulty":                                   # (difficulty REL LEVEL): AoE2 numbers, 0 is hardest
            if (level := self.game(args[1], "difficulty")) is None:
                return False
            return self.compare(args[0], bots.LEVELS[self.bot.difficulty]["aoe2"], bots.LEVELS[level]["aoe2"])
        if name == "starting-age":                                 # (starting-age REL AGE)
            import train
            return self.age_of(args[1]) is not None and \
                self.compare(args[0], train.STARTS[getattr(g, "start_age", "dark")]["ages"], self.age_of(args[1]))
        row = names().get(args[0])
        kind = name                                                # (map-type TYPE), (map-size SIZE)
        if row is None or row["kind"] != kind:
            return self.warn(kind, args[0]) or False
        return args[0] == (map_size(g.data) if kind == "map-size" else "scenario-map")

    def age_of(self, arg):
        row = names().get(arg)
        return row["age"] if row and row["kind"] == "age" else self.warn("age", arg)

    def drop_distance(self, res):
        """The distance in tiles from the nearest drop site of res to its nearest source; 255 when none (airef: -1 or a
        large value; 255 keeps a rule "< VALUE" false, as the byte limit of the game)."""
        m, T = self.bot.g.map, self.bot.g.map.T
        tiles = [t for t, k in self.bot.sources(res).items() if k > 0]
        cells = [c for d in m.drops[res] for c in d]
        if not tiles or not cells:
            return 255
        return int(min(math.dist(((t[0] + 0.5) * T, (t[1] + 0.5) * T), c) for t in tiles for c in cells) // T)

    def forage_far(self):
        """True when no fruit bush and no own sheep is within sn-maximum-food-drop-distance tiles of the town center."""
        m, T, c = self.bot.g.map, self.bot.g.map.T, self.bot.center()
        far = self.number("sn-maximum-food-drop-distance")
        far = 8 if far < 0 else far                                    # -1 is "no limit" in AoE2: the reach of a near base
        food = [t for t, k in m.bushes.items() if k > 0] + list(m.herds)
        return not c or not any(math.dist(((t[0] + 0.5) * T, (t[1] + 0.5) * T), c) <= far * T for t in food)

    def value(self, name):
        """The number of a fact (REL VALUE), or None for an unknown fact."""
        return self.fact_value(name, 0)

    def fact_value(self, name, param, g=None):
        """The number of the fact name (airef "FactId") for Gather g (default: the own one), or None for an unknown
        fact. param: the resource of escrow-amount, the unit or building of the counts, else unused (#4868)."""
        import build
        import train
        b, g = self.bot, g or self.bot.g
        if name.endswith("-amount") and (res := name.removesuffix("-amount")) in STOCK:
            return g.stock[res]
        if name in ("unit-type-count", "building-type-count", "unit-type-count-total", "building-type-count-total"):
            n = self.game(param, "unit" if name[0] == "u" else "building")
            return None if n is None else self.count(n, g, total=name.endswith("-total"))
        return {"game-time": lambda: b.time, "population": lambda: g.pop,
                "civilian-population": lambda: len(g.villagers), "military-population": lambda: len(g.soldiers),
                "housing-headroom": lambda: max(train.limit(g) - g.pop, 0),
                "population-headroom": lambda: max(train.max_pop(g) - g.pop, 0),
                "population-cap": lambda: train.limit(g), "current-age": lambda: build.ages(g),
                "current-age-time": lambda: self.age_time(g),
                "escrow-amount": lambda: self.escrow.get(param, 0) if g is b.g else 0}.get(name, lambda: None)()

    def get_fact(self, name, args):
        """up-get-fact, up-get-player-fact and up-get-fact-min, -max, -sum: the value of a fact into a goal (#4868). An
        unknown fact or player gives one warning and leaves the goal. As a fact it is true (airef "Fact/Action")."""
        if name == "up-get-fact":
            xs, (fact, param, goal) = [self.bot.g], args
        else:
            (who, fact, param, goal), xs = args, None
            xs = self.sides(who)[0] if who != self.bot.g.player else [self.bot.g]
        got = [v for x in xs if (v := self.fact_value(fact, param, x)) is not None]
        if xs and not got:
            return self.warn("fact", fact)
        if got:
            op = {"up-get-fact-min": min, "up-get-fact-max": max, "up-get-fact-sum": sum}.get(name, lambda v: v[0])
            self.goals[goal] = op(got)

    def count(self, n, g=None, total=False):
        """The live units or complete buildings of game name n of Gather g (default: the own one); total: also the
        queued units and the buildings under construction (the -total facts)."""
        import train
        if isinstance(n, tuple):
            return sum(self.count(m, g, total) for m in n)
        g = g or self.bot.g
        alive = len(g.villagers) if n.startswith("VILLAGER") else \
            sum(u == n for u in g.soldiers.values()) + train.owned(g).count(n)
        if not total:
            return alive
        like = (lambda m: m.startswith("VILLAGER")) if n.startswith("VILLAGER") else n.__eq__
        return alive + sum(like(e["name"]) for q in g.queues.values() for e in q) + \
            sum(like(s["name"]) and not s.get("done") for s in g.sites if s.get("player", g.player) == g.player)

    def age(self, g, op, arg):
        row = names().get(arg)
        if row is None or row["kind"] != "age":
            return self.warn("age", arg) or False
        import build
        return self.compare(op, build.ages(g), row["age"])

    def age_time(self, g):
        """The AoE2 seconds since the last age up of Gather g: the script sees the age change at its next check."""
        import build
        n, t = build.ages(g), self.bot.time
        if g.player not in self.aged:
            self.aged[g.player] = (n, 0.0)
        elif self.aged[g.player][0] != n:
            self.aged[g.player] = (n, t)
        return t - self.aged[g.player][1]

    def sides(self, who):
        """(the Gathers of the players of a player parameter, every): a number, focus-player (the foe of the bot), or
        any-/every- with enemy, ally, player, computer or human (airef "Facts", "Player parameters")."""
        import build
        import diplomacy
        g, b = self.bot.g, self.bot
        sides = {x.player: x for x in build.sides(g)}
        sides[g.player] = g
        if isinstance(who, int) or who == "focus-player":
            x = sides.get(b.foe if who == "focus-player" else who)
            return [x] if x else [], False
        mode, _, kind = who.partition("-")
        if mode not in ("any", "every") or kind not in ("enemy", "ally", "player", "computer", "human"):
            return self.warn("player", who) or [], False
        test = {"enemy": lambda x: diplomacy.stance(g, x.player) == "enemy",
                "ally": lambda x: diplomacy.stance(g, x.player) == "ally",
                "player": lambda x: True, "computer": lambda x: getattr(x, "share", None) is not None,
                "human": lambda x: getattr(x, "share", None) is None}[kind]
        return [x for p, x in sorted(sides.items()) if p != g.player and test(x)], mode == "every"

    def players(self, fact, who, args):
        """A fact of the other players: true for one of them (any-, a number) or for all of them (every-)."""
        xs, every = self.sides(who)
        if fact == "current-age":
            got = [self.age(x, *args) for x in xs]
        elif fact in ("building-type-count", "unit-type-count"):
            if (n := self.game(args[0], fact.split("-")[0])) is None:
                return False
            got = [self.compare(args[1], self.count(n, x), args[2]) for x in xs]
        elif fact in ("population", "military-population"):
            got = [self.compare(args[0], x.pop if fact == "population" else len(x.soldiers), args[1]) for x in xs]
        elif fact == "stance":                                     # the stance of the bot toward the player
            import diplomacy
            got = [diplomacy.stance(self.bot.g, x.player) == args[0] for x in xs]
        elif fact == "current-age-time":
            got = [self.compare(args[0], self.age_time(x), args[1]) for x in xs]
        elif fact == "civ":                                        # (players-civ PLAYER CIV)
            if (civ := self.game(args[0], "civ")) is None:
                return False
            import civs
            got = [civs.real(self.bot.g, x.player) == civ for x in xs]
        else:
            return self.warn("fact", "players-" + fact) or False
        return bool(got) and (all(got) if every else any(got))

    def forward(self):
        """The cell two thirds of the way from the own town center to the town center of the nearest enemy, or None
        (build-forward, #4654)."""
        import build
        import diplomacy
        import ruins
        g, at = self.bot.g, self.bot.center()
        foes = {x.player: x for x in build.sides(g) if diplomacy.stance(g, x.player) == "enemy"}
        tcs = [((o["footprint"][0] + o["footprint"][2]) // 2, (o["footprint"][1] + o["footprint"][3]) // 2)
               for o in g.data["objects"] if o["kind"] == "building" and o["name"] == "TOWN_CENTER"
               and o["player"] in foes and "footprint" in o and not ruins.fallen(foes[o["player"]], o)]
        if at is None or not tcs:
            return None
        far = min(tcs, key=lambda c: (c[0] - at[0]) ** 2 + (c[1] - at[1]) ** 2)
        return ((at[0] + 2 * far[0]) // 3, (at[1] + 2 * far[1]) // 3)     # 2/3 of the way: the midpoint ties with home

    def in_town(self):
        """True when a building of an enemy stands within TOWN tiles of the own town center."""
        import build
        import diplomacy
        import ruins
        g, at = self.bot.g, self.bot.center()
        if at is None:
            return False
        r = TOWN * g.data["tile_size"]
        near = lambda x, z: (x - at[0]) ** 2 + (z - at[1]) ** 2 <= r * r   # noqa: E731
        foes = {x.player: x for x in build.sides(g) if diplomacy.stance(g, x.player) == "enemy"}
        return any(o["kind"] == "building" and o["player"] in foes and "footprint" in o
                   and not ruins.fallen(foes[o["player"]], o)
                   and near((o["footprint"][0] + o["footprint"][2]) / 2, (o["footprint"][1] + o["footprint"][3]) / 2)
                   for o in g.data["objects"]) or \
            any(near((x0 + x1) / 2, (z0 + z1) / 2) for x in foes.values() for s in x.sites
                if s.get("player", x.player) == x.player for x0, x1, z0, z1 in [s["footprint"]])

    def ring(self, p):
        """The sides of the wall ring of perimeter p (lists of tiles), or None: a regular octagon around the own town
        center, with a radius in the range of PERIMETERS that keeps the own buildings in it with one free tile between
        (airef: "a roughly circular wall pattern within the given perimeter distances"). The straight sides take a
        gate of 4 tiles, the diagonal ones a gate of 3. Tiles off the map and on water are cut. The first plan stays."""
        import build

        from aoe2mc import wall_tiles
        if p not in PERIMETERS:
            return self.warn("perimeter", p)
        g, at = self.bot.g, self.bot.center()
        if p in self.rings or at is None:
            return self.rings.get(p)
        T, (lo, hi) = g.map.T, PERIMETERS[p]
        cx, cz = at[0] // T, at[1] // T
        rects = [(x0, x1, z0, z1) for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player
                 and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]] + \
            [s["footprint"] for s in g.sites if s.get("player", g.player) == g.player and s["name"] not in build.WALLS + build.GATES]
        far = [d for x0, x1, z0, z1 in rects for x in (x0 // T, (x1 - 1) // T) for z in (z0 // T, (z1 - 1) // T)
               if (d := math.ceil(max(abs(x - cx), abs(z - cz), (abs(x - cx) + abs(z - cz)) / (1 + OCTAGON)))) <= hi - 2]
        r = min(max(max(far, default=0) + 2, lo), hi)
        a = round(r * OCTAGON)
        corners = [(a, r), (r, a), (r, -a), (a, -r), (-a, -r), (-r, -a), (-r, a), (-a, r)]
        land = lambda t: all(g.map.y(*c) is not None for c in g.map.cells(t))   # noqa: E731
        self.rings[p] = [[t for t in wall_tiles(cx + x0, cz + z0, cx + x1, cz + z1)[:-1] if land(t)]   # the last tile
                         for (x0, z0), (x1, z1) in zip(corners, corners[1:] + corners[:1])]           # starts the next side
        return self.rings[p]

    def walled(self, p):
        """The percentage of the tiles of the wall ring p with a complete own wall or gate, or with a tree or a mine
        (airef: natural barriers count as complete). A ring with no tiles (all water) is complete."""
        import build
        g = self.bot.g
        tiles = [t for side in self.ring(p) for t in side]
        if not tiles:
            return 100
        done = {t for t, s in build.wall_tiles_of(g).items() if s is None or s["progress"] >= 1}
        done |= {t for s in g.sites if s["name"] in build.GATES and s.get("player", g.player) == g.player
                 and s["progress"] >= 1 for t in self.gate_tiles(s)}
        barrier = lambda t: g.map.trees.get(t, 0) > 0 or any(c in g.map.mine_at for c in g.map.cells(t))   # noqa: E731
        return 100 * sum(t in done or barrier(t) for t in tiles) // len(tiles)

    def gate_tiles(self, site):
        T = self.bot.g.map.T
        x0, x1, z0, z1 = site["footprint"]
        return {tuple(t) for t in site.get("tiles") or
                [(x, z) for x in range(x0 // T, x1 // T) for z in range(z0 // T, z1 // T)]}

    def wall(self, p, kind):
        """(build-wall PERIMETER WALL-TYPE): sites on the free tiles of one side of the ring p, as many as the stock
        without the escrow pays; the side nearest to the enemy first. One villager builds them, as a wall line of a
        player (the key "line": build.next_tile)."""
        import build
        g, b = self.bot.g, self.bot
        if (n := self.game(kind, "building")) is None or not (sides := self.ring(p)) or build.locked(g, n):
            return
        if n not in build.WALLS:
            return self.warn("wall", kind)
        T, to = g.map.T, self.forward()
        if to:
            sides = sorted(sides, key=lambda s: min((math.dist((x * T, z * T), to) for x, z in s), default=math.inf))
        cost = build.price(g, n)
        for side in sides:
            rects = [r for x, z in side if build.free(g, r := (x * T, (x + 1) * T, z * T, (z + 1) * T))]
            if rects:
                k = min([len(rects)] + [(g.stock[r] - self.escrow.get(r, 0)) // v for r, v in cost.items() if v])
                sites = [build.found(g, n, r) for r in rects[:max(k, 0)]]
                for s in sites:
                    s["line"] = rects[0]
                if sites:
                    b.builder(sites[0])
                return

    def gate(self, p):
        """(build-gate PERIMETER): a gate on own wall tiles near the middle of a side of the ring p with no gate yet
        (build.gate): first on the straight sides (4 tiles, airef: "replace four wall segments"), then on the diagonal
        ones (3 tiles). sn-gate-type-for-wall 1: a palisade gate (airef)."""
        import build
        g, b = self.bot.g, self.bot
        n = self.game("palisade-gate" if self.number("sn-gate-type-for-wall") == 1 else "gate", "building")
        if not n or not (sides := self.ring(p)) or build.locked(g, n) or not self.paid(build.price(g, n)):
            return
        T = g.map.T
        gated = {t for s in g.sites if s["name"] in build.GATES and s.get("player", g.player) == g.player
                 for t in self.gate_tiles(s)}
        for side in sorted(sides, key=lambda s: min(len({x for x, _ in s}), len({z for _, z in s})) > 1):   # straight first
            if gated & set(side):
                continue
            for i in sorted(range(len(side)), key=lambda i: (abs(2 * i - len(side) + 1), i)):   # the middle first
                cell = side[i][0] * T, side[i][1] * T
                if (spot := build.gate_spot(g, cell)) and set(map(tuple, spot[2])) <= set(side):
                    site = build.gate(g, b.nobody, n, cell)
                    if site and not any(v.site is site for v in g.villagers.values()):
                        b.builder(site)
                    return

    def paid(self, cost, escrow=False):
        """The stock pays cost; the escrow pays only with escrow (the -with-escrow facts)."""
        return all(self.bot.g.stock[r] - (0 if escrow else self.escrow.get(r, 0)) >= v for r, v in cost.items())

    def homes(self, n):
        """The block cells of the own buildings that offer n now."""
        import build
        import train
        g = self.bot.g
        if build.locked(g, n):
            return []
        return [(rect[0], rect[2]) for rect, home in sorted(train.homes(g).items()) if n in train.trains(g, home)]

    def can(self, name, arg, escrow=False):
        import build
        import train
        g = self.bot.g
        if name == "can-build":
            n = self.game(arg, "building")
            return bool(n and g.villagers and not build.locked(g, n) and self.paid(build.price(g, n), escrow))
        n = self.game(arg, "unit") if name == "can-train" else self.game(arg, "tech", "age")
        if n is None:
            return False
        if name == "research-completed":
            return train.researched(g, n)
        if name in ("can-research", "research-available") and (train.researched(g, n) or train.queued(g, n)):
            return False
        if name == "can-train" and g.pop >= train.limit(g):
            return False
        return bool(self.homes(n)) and (name == "research-available" or self.paid(train.price(g, n), escrow))

    def trade_ok(self, buy, res):
        """A trade of 100 res is possible now: an own market and the gold (a buy) or the resource (a sell)."""
        import market
        g = self.bot.g
        if res not in market.RATES:
            return self.warn("commodity", res) or False
        return bool(market.markets(g)) and (g.stock["gold"] >= market.price(g, res, True) if buy
                                            else g.stock[res] >= market.LOT)

    def act(self, k, a):
        import build
        import train
        name, args, b = a[0], a[1:], self.bot
        g = b.g
        if name in ("train", "research"):
            n = self.game(args[0], "unit") if name == "train" else self.game(args[0], "tech", "age")
            if n and self.can("can-" + name, args[0]):
                next((c for c in self.homes(n) if train.queue(g, b.nobody, c, n)), None)
        elif name in ("build", "build-forward"):
            n = self.game(args[0], "building")
            center = b.center() if name == "build" else self.forward()
            if n and self.can("can-build", args[0]) and center and (rect := build.near(g, n, center)) is not None:
                b.builder(build.found(g, n, rect))
        elif name == "build-wall":                                     # (build-wall PERIMETER WALL-TYPE)
            self.wall(args[0], args[1])
        elif name == "build-gate":                                     # (build-gate PERIMETER)
            self.gate(args[0])
        elif name == "disable-self":
            self.off.add(k)
        elif name == "set-goal":
            self.goals[args[0]] = args[1]
        elif name == "set-strategic-number":
            args = (SN_IDS.get(args[0], args[0]),) + tuple(args[1:])
            if args[0] not in SN:
                return self.warn("strategic number", args[0])
            self.sn[args[0]] = args[1]
        elif name in GET_FACT:
            self.get_fact(name, args)
        elif name == "up-modify-goal":                               # (up-modify-goal GOAL OP VALUE)
            new = self.math(args[1], self.goals.get(args[0], -1), args[2])
            if new is not None:
                self.goals[args[0]] = new
        elif name == "up-modify-sn":                                 # (up-modify-sn SN OP VALUE)
            sn = SN_IDS.get(args[0], args[0])
            if sn not in SN:
                return self.warn("strategic number", sn)
            new = self.math(args[1], self.number(sn), args[2])
            if new is not None:
                self.sn[sn] = new
        elif name == "up-jump-rule":                                 # (up-jump-rule DELTA): the rule k + 1 + DELTA
            self.jump = k + 1 + args[0]
        elif name == "up-jump-direct":                               # (up-jump-direct TYPE ID): the rule ID (from 0)
            n = self.jump_to(args[0], args[1])
            if n is not None:
                self.jump = n
        elif name == "up-jump-dynamic":                              # (up-jump-dynamic TYPE DELTA): k + 1 + DELTA
            n = self.jump_to(args[0], args[1])
            if n is not None:
                self.jump = k + 1 + n
        elif name == "up-get-rule-id":                               # (up-get-rule-id GOAL): the rule k of the goal
            self.goals[args[0]] = k
        elif name == "set-escrow-percentage":                    # (set-escrow-percentage RESOURCE PCT)
            if args[0] not in STOCK:
                return self.warn("resource", args[0])
            self.pct[args[0]] = min(max(args[1], 0), 100)
        elif name == "release-escrow":
            self.escrow.pop(args[0], None)
        elif name == "attack-now":
            self.attacking = True
        elif name == "enable-timer":
            self.timers[args[0]] = b.time + args[1]
        elif name == "disable-timer":
            self.timers.pop(args[0], None)
        elif name == "set-stance":                                 # the path of the player menu; a locked team stays
            import diplomacy
            if g.data.get("unlock_teams") and args[1] in diplomacy.STANCES:
                for _ in diplomacy.STANCES:
                    if diplomacy.stance(g, args[0]) == args[1]:
                        break
                    diplomacy.change(g, None, args[0])
        elif name == "chat-to-all":
            g.command("tellraw @a " + json.dumps({"text": f"<Player {g.player}> {args[0]}"}))
        elif name == "chat-to-player":                              # only the people of that seat (team pN)
            g.command(f"tellraw @a[team=p{args[0]}] " + json.dumps({"text": f"<Player {g.player}> {args[1]}"}))
        elif name in ("buy-commodity", "sell-commodity"):           # the path of the market menu (#4573)
            import market
            if self.trade_ok(name == "buy-commodity", args[0]):
                market.trade(g, b.nobody, args[0], name == "buy-commodity")
        elif name == "tribute-to-player":                           # (tribute-to-player PLAYER RESOURCE AMOUNT)
            import diplomacy
            if args[1] not in STOCK:
                return self.warn("resource", args[1])
            for _ in range(max(args[2], 0) // diplomacy.LOT):        # one tribute of the menu per 100
                if not diplomacy.send(g, b.nobody, args[0], args[1]):
                    break
        elif name == "acknowledge-taunt":                            # (acknowledge-taunt PLAYER TAUNT)
            self.heard.discard((args[0], args[1]))
        elif name not in ("do-nothing", "chat-local-to-self", "enable-wall-placement"):
            # no one sees a self chat; each wall ring is always enabled (ring())
            self.warn("action", name)
