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

import numpy as np

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
VICTORY_TYPES = {                  # run.py --victory: the airef VictoryType; one per line, in alphabetical order
    "conquest": 1,
    "last-man-standing": 1,
    "score": 3,
    "standard": 0,
    "time-limit": 2,
}
GET_FACT = ("up-get-fact", "up-get-fact-max", "up-get-fact-min", "up-get-fact-sum", "up-get-player-fact")
COST_ACTIONS = ("up-setup-cost-data", "up-reset-cost-data", "up-add-cost-data", "up-add-object-cost",
                "up-add-research-cost", "up-get-cost-delta")
COST_GOODS = ("food", "wood", "stone", "gold")   # a cost set is 4 goals in a row, in this order (airef "Cost data", #4879)
STOCK = ("food", "wood", "gold", "stone")
IN_TOWN = ("up-building-type-in-town", "up-enemy-buildings-in-town", "up-enemy-units-in-town",   # #4874
           "up-enemy-villagers-in-town", "up-unit-type-in-town", "up-villager-type-in-town")
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
# The airef ids of objects and technologies (two sets of numbers): the up-* commands with g: take an id (#4869).
OBJECT_IDS = {r["id"]: r["name"] for r in table.load("per_names.jsonl") if "id" in r and r["kind"] in ("unit", "building")}
TECH_IDS = {r["id"]: r["name"] for r in table.load("per_names.jsonl") if "id" in r and r["kind"] in ("tech", "age")}
SHARED = ("up-get-event", "up-get-shared-goal", "up-get-signal", "up-set-event", "up-set-shared-goal", "up-set-signal")
POINTS = ("up-add-point", "up-bound-point", "up-bound-precise-point", "up-copy-point", "up-cross-tiles",   # #4956
          "up-get-point", "up-get-point-distance", "up-lerp-percent", "up-lerp-tiles", "up-set-precise-target-point",
          "up-set-target-point")
UP_QUEUE = {"up-build": "build", "up-research": "research", "up-train": "train"}
ORDERS = ("up-delete-distant-farms", "up-delete-idle-units", "up-reset-attack-now", "up-reset-building",
          "up-reset-unit", "up-retreat-now")


SETUP = ("civ-selected", "death-match-game", "difficulty", "map-size", "map-type", "regicide-game", "starting-age")
FIND_METHODS = {"find-attacker": 0,                                # airef "FindPlayerMethod" (up-find-player)
                "find-closest": 2,
                "find-ordered": 3,
                "find-random": 1}
RESEARCH_STATE = {"research-available": 1,                         # airef "ResearchState" (up-research-status)
                  "research-complete": 3,
                  "research-pending": 2,
                  "research-queued": 4,
                  "research-unavailable": 0}
TIMER_STATE = {"timer-disabled": 0,                                # the states of up-timer-status (airef "TimerState")
               "timer-running": 2,
               "timer-triggered": 1}


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
        self.rng = np.random.default_rng(bot.g.player)               # find-random of up-find-player (#4872)
        self.unplaced = set()                                      # the buildings of build with no free site (#4870)
        self.text, self.name = "", None                            # the text buffer of up-store-*; up-change-name (#4877)
        self.heard, self.read = set(), {}                          # (player, taunt) not acknowledged; player -> read
        self.jump = None                                           # the rule after the actions of this rule (up-jump-*)
        self.cost_at = None                                        # the first goal of the current cost set (#4879)
        self.builders = {}                                         # building -> builders of up-assign-builders (#4875)
        self.scouts = []                                           # the scouts of up-send-scout (#4969)
        self.point = None                                          # (x, y) tiles of up-set-target-point (#4956)

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

    def table(self, kind):
        """The values of the shared goals, signals or events (#4878). Shared goals: one table per team on the main Gather
        (conquest.main), so each allied script reads the same value (airef "up-set-shared-goal"). Signals and events:
        the game program has no scenario trigger "AI signal" or effect "AI trigger" yet, so the script keeps them."""
        if kind != "shared-goal":
            return vars(self).setdefault(kind + "s", {})                   # signals, events
        from conquest import main  # conquest imports gather, which imports this module
        g = self.bot.g
        team = (g.players.get(str(g.player)) or {}).get("team")
        return vars(main(g)).setdefault("shared_goals", {}).setdefault(("p", g.player) if team is None else team, {})

    def shared(self, name, args):
        """up-get-X TYPE ID GOAL: the value of shared goal, signal or event ID into GOAL (0 when not set);
        up-set-X TYPE ID TYPE2 VALUE: set it."""
        values = self.table(name.split("-", 2)[2])
        kind = self.type_kind(args[0])
        ref = self.operand(kind, args[1]) if kind else None
        if ref is None:
            return
        if name.startswith("up-get-"):
            self.goals[args[2]] = values.get(ref, 0)
        elif (kind2 := self.type_kind(args[2])) and (value := self.operand(kind2, args[3])) is not None:
            values[ref] = value

    def named(self, type_op, ref, tech=False):
        """The script name of an object (or a technology) of an up-* command: c: a name or an id, g: a goal that holds
        an id. None, with one warning, for an unknown id."""
        kind = self.type_kind(type_op)
        ref = self.operand(kind, ref) if kind else None
        if isinstance(ref, int):
            return (TECH_IDS if tech else OBJECT_IDS).get(ref) or self.warn("id", ref)
        return ref

    def type_kind(self, type_op):
        """The kind of a typeOp (airef "typeOp": c:, g: or s:, no relation). None, with one warning, for another one."""
        if type_op in ("c:", "g:", "s:"):
            return type_op[0]
        return self.warn("operator", type_op)

    def typed(self, prefix, ref):
        """operand() for a type prefix of a timer command ("", c:, g: or s:); None, with one warning, for another one."""
        kind = str(prefix).removesuffix(":")
        if kind not in ("", "c", "g", "s"):
            return self.warn("operator", prefix)
        return self.operand(kind, ref)

    def timer_state(self, tid):
        """The TIMER_STATE of timer tid: disabled (no entry), triggered (the game time is due) or running."""
        due = self.timers.get(tid)
        if due is None:
            return TIMER_STATE["timer-disabled"]
        return TIMER_STATE["timer-triggered" if self.bot.time >= due else "timer-running"]

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
        if name == "up-point-distance":                            # (up-point-distance P1 P2 REL VALUE)
            d = self.point_distance(args[0], args[1])
            return d is not None and self.compare(args[2], d, args[3])
        if name == "up-compare-text":                              # (up-compare-text TEXT REL): the text buffer
            return self.compare(args[1], self.text, str(args[0]))
        if name == "up-compare-goal":                              # (up-compare-goal GOAL REL VALUE)
            return self.compare(args[1], self.goals.get(args[0], -1), args[2])
        if name == "up-compare-sn":                                # (up-compare-sn SN REL VALUE)
            sn = SN_IDS.get(args[0], args[0])
            if sn not in SN:
                return self.warn("strategic number", sn) or False
            return self.compare(args[1], self.number(sn), args[2])
        if name == "up-compare-const":                             # (up-compare-const CONST REL VALUE)
            return self.compare(args[1], args[0], args[2])
        if name == "up-compare-flag":                              # (up-compare-flag GOAL OP FLAG): == all bits, != not
            kind, _, rel = args[1].rpartition(":")
            if rel not in ("==", "!=") or kind not in ("", "c", "s", "g"):
                return self.warn("operator", args[1]) or False
            flag = self.operand(kind, args[2])
            if flag is None:
                return False
            has = self.goals.get(args[0], 0) & flag
            return has == flag if rel == "==" else has != flag
        if name == "strategic-number":                             # (strategic-number NAME REL VALUE)
            args = (SN_IDS.get(args[0], args[0]),) + tuple(args[1:])
            if args[0] not in SN:
                return self.warn("strategic number", args[0]) or False
            return self.compare(args[1], self.sn.get(args[0], SN[args[0]]), args[2])
        if name == "timer-triggered":
            return args[0] in self.timers and self.bot.time >= self.timers[args[0]]
        if name == "up-timer-status":                              # (up-timer-status TIMER REL STATE)
            state = TIMER_STATE.get(args[2], args[2])
            if not isinstance(state, int):
                return self.warn("timer state", args[2]) or False
            return self.compare(args[1], self.timer_state(args[0]), state)
        if name in ("true", "false"):
            return name == "true"
        if name == "stance-toward":                                # (stance-toward PLAYER STANCE)
            import diplomacy
            return diplomacy.stance(self.bot.g, args[0]) == args[1]
        if name in ("can-train", "can-build", "can-research", "research-available", "research-completed"):
            return self.can(name, args[0])
        if name in ("can-train-with-escrow", "can-build-with-escrow", "can-research-with-escrow"):
            return self.can(name.removesuffix("-with-escrow"), args[0], True)
        if name in ("up-can-train", "up-can-build", "up-can-research"):     # (up-can-train ESCROW TYPE UNIT)
            sn = self.named(args[1], args[2], name == "up-can-research")
            return sn is not None and self.can(name.removeprefix("up-"), sn, self.goals.get(args[0], 0) >= 1)
        if name in ("up-pending-objects", "up-pending-placement", "up-research-status", "up-train-site-ready"):
            return self.pending(name, args)
        if name in ("up-object-type-count", "up-object-type-count-total"):    # (up-object-type-count TYPE OBJECT REL VALUE)
            if (sn := self.named(args[0], args[1])) is None or (n := self.game(sn, "unit", "building")) is None:
                return False
            return self.compare(args[2], self.count(n, total=name.endswith("-total")), args[3])
        if name in ("up-gaia-type-count", "up-gaia-type-count-total"):  # (up-gaia-type-count TYPE OBJECT REL VALUE)
            if (sn := self.named(args[0], args[1])) is None:
                return False
            return self.compare(args[2], self.gaia(sn, total=name.endswith("-total")), args[3])
        if name == "up-remaining-boar-amount":                     # (up-remaining-boar-amount REL VALUE)
            return self.compare(args[0], self.boar(), args[1])
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
        if name in ("up-players-in-game", "up-player-distance", "up-allied-goal", "up-allied-sn"):
            return self.others(name, args)
        if name == "enemy-buildings-in-town":
            return self.in_town()
        if name in IN_TOWN:
            return self.in_town_count(name, args)
        if name == "up-defender-count":                            # (up-defender-count REL VALUE): guards and defenders
            return self.compare(args[0], len(self.bot.guards) + len(self.bot.defense), args[1])
        if name == "up-idle-unit-count":                           # (up-idle-unit-count IDLE-TYPE REL VALUE)
            return self.idle_count(args[0], args[1], args[2])
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

    def victory_data(self, name, args):
        """up-get-victory-data PLAYER TYPE TIME, up-get-victory-limit GOAL, up-get-treaty-data GOAL (#4873). A value
        that the game program does not have gives 0."""
        import time_limit  # it imports cheats -> gather: import it late
        g = self.bot.g
        mode = getattr(g, "victory", "standard")
        if name == "up-get-victory-data":                          # the wonder or relic timer that ends first
            left = [(t["left"], t["player"]) for t in vars(g).get("wonders", {}).values()]
            if t := vars(g).get("relic_timer"):
                left.append((t["left"], t["player"]))
            time, player = min(left, default=(0, 0))
            self.goals[args[0]], self.goals[args[1]] = player, VICTORY_TYPES.get(mode, 0)
            self.goals[args[2]] = max(math.ceil(time), 0)
        elif name == "up-get-victory-limit":                       # the years of a time limit, the points of a score
            value = getattr(g, "victory_value", None)
            self.goals[args[0]] = {"time-limit": value or time_limit.YEARS, "score": value or time_limit.POINTS}.get(mode, 0)
        else:                                                      # the treaty seconds left; a treaty with no end: the max
            game = getattr(g, "game", None)
            left = max(getattr(game, "treaty", 0.0) - getattr(game, "treaty_time", 0.0), 0)
            self.goals[args[0]] = 2 ** 31 - 1 if math.isinf(left) else math.ceil(left)

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

    def cost_action(self, name, args):
        """The up-*-cost-data actions (#4879). A cost set is 4 goals in a row (COST_GOODS). A value is an operand of
        kind TYPE (airef "Typed operators"): a constant, a goal or a strategic number. An action that adds to the current
        set needs up-setup-cost-data first."""
        if name == "up-setup-cost-data":                              # (up-setup-cost-data RESET GOAL)
            self.cost_at = args[1]
            if args[0] == 1:
                self.cost_zero(args[1])
            return
        if name == "up-reset-cost-data":                              # (up-reset-cost-data GOAL)
            return self.cost_zero(args[0])
        if self.cost_at is None:
            return self.warn("cost data", name)
        if name == "up-get-cost-delta":                               # (up-get-cost-delta GOAL): stock - current set
            for i, r in enumerate(COST_GOODS):
                self.goals[args[0] + i] = self.bot.g.stock[r] - self.goals.get(self.cost_at + i, 0)
        elif name == "up-add-cost-data":                              # (up-add-cost-data GOAL TYPE VALUE)
            src = {r: self.goals.get(args[0] + i, 0) for i, r in enumerate(COST_GOODS)}
            self.cost_add(self.cost_at, src, args[1], args[2])
        elif name == "up-add-object-cost":                            # (up-add-object-cost TYPE OBJECT TYPE2 VALUE)
            import build
            import train
            ns = self.game(args[1], args[0])                          # a set adds the costs of its members
            price = build.price if args[0] == "building" else train.price
            cost = {}
            for n in (ns if isinstance(ns, tuple) else (ns,) if ns else ()):
                for r, v in price(self.bot.g, n).items():
                    cost[r] = cost.get(r, 0) + v
            self.cost_add(self.cost_at, cost, args[2], args[3])
        elif name == "up-add-research-cost":                          # (up-add-research-cost TECH TYPE VALUE)
            import train
            n = self.game(args[0], "tech", "age")
            if n:
                self.cost_add(self.cost_at, train.price(self.bot.g, n), args[1], args[2])

    def cost_zero(self, first):
        """The 4 goals of the cost set that starts at first are 0."""
        for i in range(len(COST_GOODS)):
            self.goals[first + i] = 0

    def cost_add(self, first, cost, kind, ref):
        """Add the operand (kind, ref) times cost, a dict of the stock resources, to the cost set that starts at first."""
        value = self.operand(kind, ref)
        if value is None:
            return
        for i, r in enumerate(COST_GOODS):
            self.goals[first + i] = self.goals.get(first + i, 0) + value * cost.get(r, 0)

    def gaia(self, sn, total=False):
        """The gaia objects (player 0 of aoe2mc.json) of script name sn (gold-mine: GOLD_MINE; tree: each TREE_*) on the
        tiles that the team of the bot sees now (Gather.seen_tiles with fog.shares); total: also the ones that it saw
        once (airef up-gaia-type-count-total)."""
        import fog
        g, n = self.bot.g, str(sn).upper().replace("-", "_")
        tiles = set().union(*(h.seen_tiles() for h in fog.gathers(g) if fog.shares(g, h)))
        mine = {i for i, o in enumerate(g.data["objects"]) if o.get("player", 0) == 0 and "tile" in o
                and (o["name"] == n or o["name"].startswith(n + "_"))}
        now = {i for i in mine if tuple(int(c) for c in g.data["objects"][i]["tile"][:2]) in tiles}
        self.saw = vars(self).get("saw", set()) | now
        return len(self.saw & mine if total else now)

    def boar(self):
        """The food of the boar that a villager of the bot hunts now (Gather.hunt): the carcass food after the kill, else
        the full HUNT_FOOD; 0 when no villager hunts a boar."""
        import gather
        g = self.bot.g
        out = 0
        for v in g.villagers.values():
            name = g.prey.get(v.prey or "", "")
            if "BOAR" in name or "JAVELINA" in name:
                out = max(out, g.map.carcasses.get(g.dead[v.prey], 0) if v.prey in g.dead else gather.hunt_food(name))
        return out

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

    def tiles(self):
        """The width of the map in tiles."""
        d = self.bot.g.data
        return len(d.get("ground", ())) // d.get("tile_size", 1)

    def pair(self, goal):
        """The point (x, y) of the goal pair goal, goal + 1; goal 0: the target point (airef "Point"). None: no point."""
        if goal == 0:
            return self.point
        if goal not in self.goals or goal + 1 not in self.goals:
            return self.warn("goal", goal)
        return self.goals[goal], self.goals[goal + 1]

    def store(self, goal, p):
        self.goals[goal], self.goals[goal + 1] = int(p[0]), int(p[1])

    def bound(self, p, border=0, n=None):
        n = self.tiles() if n is None else n
        return tuple(min(max(int(v), border), n - 1 - border) for v in p)

    def town_tile(self, player):
        """The tile (x, y) of the first town center of player, or None."""
        g = self.bot.g
        tc = next((o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o.get("player") == player
                   and o["name"] == "TOWN_CENTER" and "footprint" in o), None)
        T = g.data["tile_size"]
        return tc and ((tc[0] + tc[2]) // 2 // T, (tc[1] + tc[3]) // 2 // T)

    def position(self, kind):
        """The tile (x, y) of an airef PositionType, or None (the script gets (-1, -1)). The game program has no map
        facts of the teams: mirror reflects across the long axis to the town, flank is the enemy town."""
        n, b = self.tiles(), self.bot
        me = self.town_tile(b.g.player)
        c = (n // 2, n // 2)
        foe = self.town_tile(b.foe) if b.foe is not None else None
        if kind == "position-center":
            return c
        if kind == "position-zero":
            return 0, 0
        if kind == "position-map-size":
            return n - 1, n - 1
        if kind in ("position-target", "position-point"):
            return self.point
        if kind == "position-object":
            return self.warn("position", kind)                      # the target object: the object search ticket
        if kind in ("position-enemy", "position-focus", "position-flank"):
            return foe or (kind == "position-enemy" and self.position("position-opposite")) or None
        if me is None:
            return None
        if kind == "position-self":
            return me
        if kind == "position-opposite":
            return n - 1 - me[0], n - 1 - me[1]
        if kind == "position-mirror":                              # across the axis of the map that is nearer
            return (n - 1 - me[0], me[1]) if abs(me[0] - c[0]) >= abs(me[1] - c[1]) else (me[0], n - 1 - me[1])
        if kind == "position-corner":
            return tuple(0 if v < n / 2 else n - 1 for v in me)
        if kind == "position-border":
            x, y = me
            return min([(0, y), (n - 1, y), (x, 0), (x, n - 1)], key=lambda p: math.dist(p, me))
        return self.warn("position", kind)

    def point_distance(self, a, b):
        p, q = self.pair(a), self.pair(b)
        return None if p is None or q is None else int(math.dist(p, q))

    def send_scout(self, group, method):
        """Walk the land scouts (stance.SCOUT_NAMES, at most sn-total-number-explorers) to the tile of an airef
        ScoutMethod: the PositionType of the same name (scout-opposite: position-opposite). The mob AI walks them."""
        import stance
        g = self.bot.g
        if group != "group-type-land-explore":
            return self.warn("group type", group)
        if method not in ("scout-border", "scout-center", "scout-corner", "scout-enemy", "scout-flank", "scout-mirror",
                          "scout-opposite"):                       # airef pScoutMethod
            return self.warn("scout method", method)
        if (p := self.position("position" + method[5:])) is None:
            return
        units = [u for u in sorted(g.soldiers) if g.soldiers[u] in stance.SCOUT_NAMES][:max(self.number("sn-total-number-explorers"), 0)]
        if not units:
            return
        g.new_order(units)
        T = g.data["tile_size"]
        x, z = (v * T + T // 2 for v in self.bound(p))
        for u in units:
            g.command(f"aoe moveto {u} {x} {g.map.y(x, z)} {z}")
        self.scouts = sorted(set(self.scouts) | set(units))

    def points(self, name, args):
        """The point commands of UserPatch (airef, #4956): a point is a goal pair (x, y) in tiles, a precise point
        tiles × 100."""
        if name == "up-get-point":                                 # (up-get-point POSITION GOAL)
            p = self.position(args[0])
            if p is not None or args[0] != "position-object":
                self.store(args[1], p if p is not None else (-1, -1))
            return
        if name in ("up-set-target-point", "up-set-precise-target-point"):     # (up-set-target-point GOAL)
            p = self.pair(args[0])
            if p is not None:
                self.point = self.bound(p) if name == "up-set-target-point" else tuple(p)
            return
        if name == "up-bound-precise-point":                       # (up-bound-precise-point GOAL OPTION TYPE VALUE)
            p, kind = self.pair(args[0]), self.type_kind(args[2])
            v = self.operand(kind, args[3]) if kind else None
            if p is not None and v is not None:
                self.store(args[0], self.bound(p, v, self.tiles() * (100 if args[1] == 1 else 1)))
            return
        if name == "up-get-point-distance":                        # (up-get-point-distance P1 P2 GOAL)
            d = self.point_distance(args[0], args[1])
            if d is not None:
                self.goals[args[2]] = d
            return
        q = self.pair(args[1])
        if q is None:
            return
        if name == "up-copy-point":                                # (up-copy-point P1 P2)
            return self.store(args[0], q)
        if name == "up-bound-point":                               # (up-bound-point P1 P2)
            return self.store(args[0], self.bound(q))
        p, kind = self.pair(args[0]), self.type_kind(args[2])
        v = self.operand(kind, args[3]) if kind else None
        if p is None or v is None:
            return
        dx, dy = q[0] - p[0], q[1] - p[1]
        d = math.hypot(dx, dy) or 1
        if name == "up-add-point":                                 # (up-add-point P1 P2 TYPE VALUE): P1 + VALUE × P2
            out = (p[0] + v * q[0], p[1] + v * q[1])
        elif name == "up-lerp-percent":                            # VALUE percent of the way from P1 to P2
            out = (p[0] + dx * v / 100, p[1] + dy * v / 100)
        elif name == "up-lerp-tiles":                              # VALUE tiles from P1 toward P2
            out = (p[0] + dx / d * v, p[1] + dy / d * v)
        else:                                                      # up-cross-tiles: VALUE tiles to the right of P1 -> P2
            out = (p[0] - dy / d * v, p[1] + dx / d * v)
        self.store(args[0], tuple(round(c) for c in out))

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

    def stanced(self, stance):
        """The other players (Gathers by player number) of a playerStance: any, ally, neutral or enemy (#4872)."""
        import build
        import diplomacy
        g = self.bot.g
        xs = {x.player: x for x in build.sides(g) if x.player != g.player}
        return {p: x for p, x in sorted(xs.items()) if stance == "any" or diplomacy.stance(g, p) == stance}

    def distance(self, x):
        """Tiles from the own town center to the nearest building or site of the Gather x; None with none."""
        import ruins
        g, at = self.bot.g, self.bot.center()
        rects = [o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o.get("player") == x.player
                 and "footprint" in o and not ruins.fallen(x, o)]
        rects += [(x0, z0, x1, z1) for s in x.sites if s.get("player", x.player) == x.player
                  for x0, x1, z0, z1 in [s["footprint"]]]
        if at is None or not rects:
            return None
        return min(math.hypot((r[0] + r[2]) / 2 - at[0], (r[1] + r[3]) / 2 - at[1]) for r in rects) / g.data["tile_size"]

    def others(self, name, args):
        """up-players-in-game STANCE REL VALUE, up-player-distance PLAYER REL VALUE, up-allied-goal PLAYER GOAL REL
        VALUE, up-allied-sn PLAYER SN REL VALUE (#4872): the goal or number of the script of an allied bot."""
        import build
        import diplomacy
        g = self.bot.g
        if name == "up-players-in-game":
            return self.compare(args[1], len(self.stanced(args[0])), args[2])
        x = self.stanced("any").get(args[0])
        if name == "up-player-distance":
            d = None if x is None else self.distance(x)
            return d is not None and self.compare(args[1], round(d), args[2])
        first = (build.sides(g) or [g])[0]
        other = next((b.script for b in getattr(first, "bots", ()) if b.g.player == args[0]), None)
        if other is None or diplomacy.stance(g, args[0]) != "ally":
            return False
        if name == "up-allied-goal":
            return self.compare(args[2], other.goals.get(args[1], -1), args[3])
        sn = SN_IDS.get(args[1], args[1])
        return sn in SN and self.compare(args[2], other.number(sn), args[3])

    def find_player(self, name, args):
        """(up-find-player STANCE METHOD GOAL), up-find-next-player: a player of airef "FindPlayerMethod" into the goal,
        0 for none. find-attacker: the game program keeps no attacker, so 0. Next: after the player in the goal."""
        xs = self.stanced(args[0])
        if name == "up-find-next-player":
            after = self.goals.get(args[2], 0)
            xs = {p: x for p, x in xs.items() if p != after}
        method = FIND_METHODS.get(args[1], args[1])
        if not xs or method == 0:
            pick = 0
        elif method == 1:
            pick = int(self.rng.choice(sorted(xs)))
        elif method == 2:
            near = {p: d for p, x in xs.items() if (d := self.distance(x)) is not None}
            pick = min(near, key=lambda p: (near[p], p), default=0)
        else:
            pick = max(xs)
        if name == "up-find-next-player" and method == 3:          # ordered: the next lower player, then from the top
            after = self.goals.get(args[2], 0)
            pick = max((p for p in xs if p < after), default=max(xs, default=0))
        self.goals[args[2]] = pick

    def in_town(self):
        """True when a building of an enemy stands within TOWN tiles of the own town center."""
        return bool(self.town()["building"])

    def town(self):
        """The game names of the enemy objects within TOWN tiles of the own town center: {"building": [...], "villager":
        [...], "soldier": [...]}. A building: also a site under construction (#4874)."""
        import build
        import diplomacy
        import ruins
        g, at = self.bot.g, self.bot.center()
        out = {"building": [], "villager": [], "soldier": []}
        if at is None:
            return out
        r = TOWN * g.data["tile_size"]
        near = lambda x, z: (x - at[0]) ** 2 + (z - at[1]) ** 2 <= r * r   # noqa: E731
        foes = {x.player: x for x in build.sides(g) if diplomacy.stance(g, x.player) == "enemy"}
        out["building"] = [o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] in foes
                           and "footprint" in o and not ruins.fallen(foes[o["player"]], o)
                           and near((o["footprint"][0] + o["footprint"][2]) / 2, (o["footprint"][1] + o["footprint"][3]) / 2)]
        out["building"] += [s["name"] for x in foes.values() for s in x.sites if s.get("player", x.player) == x.player
                            for x0, x1, z0, z1 in [s["footprint"]] if near((x0 + x1) / 2, (z0 + z1) / 2)]
        out["villager"] = ["VILLAGER_MALE" for x in foes.values()
                           for v in x.villagers.values() if v.pos and near(v.pos[0], v.pos[2])]
        out["soldier"] = [x.soldiers[u] for x in foes.values() for u, p in x.positions(sorted(x.soldiers)).items()
                          if near(p[0], p[2])]
        return out

    def in_town_count(self, name, args):
        """The facts up-*-in-town (#4874): (up-enemy-units-in-town REL VALUE), (up-building-type-in-town TYPE BUILDING
        REL VALUE) and the other ones. A unit: a villager or a soldier; a -type- fact counts only its object."""
        objs = self.town()
        part = name.removeprefix("up-").removesuffix("-in-town").removeprefix("enemy-")
        part = part.removesuffix("-type").removesuffix("s")
        found = objs["villager"] + objs["soldier"] if part == "unit" else objs[part]
        if "-type-" in name:
            if (sn := self.named(args[0], args[1])) is None or not (n := self.game(sn, "unit", "building")):
                return False
            want = set(n) if isinstance(n, tuple) else {n}
            same = lambda k: k in want or k.startswith("VILLAGER") and any(w.startswith("VILLAGER") for w in want)   # noqa: E731
            found, args = [k for k in found if same(k)], args[2:]
        return self.compare(args[0], len(found), args[1])

    def idle_count(self, kind, op, value):
        """up-idle-unit-count: idle-villagers (Gather.idle) or idle-military (no target of a wave or of the town defense)."""
        b = self.bot
        if kind == "idle-villagers":
            n = sum(v.state == "idle" for v in b.g.villagers.values())
        elif kind == "idle-military":
            n = len(b.g.soldiers.keys() - b.targets.keys() - b.guards.keys())
        else:
            return self.warn("idle type", kind) or False
        return self.compare(op, n, value)

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

    def spend(self, cost):
        """A command with escrow paid cost: the escrow pays it first (airef "up-train")."""
        for r, v in cost.items():
            if (e := self.escrow.get(r, 0) - v) > 0:
                self.escrow[r] = e
            else:
                self.escrow.pop(r, None)

    def pending(self, name, args):
        """up-pending-objects TYPE OBJECT REL VALUE (queued units and unfinished sites), up-pending-placement TYPE
        BUILDING, up-research-status TYPE TECH REL STATE (RESEARCH_STATE), up-train-site-ready TYPE UNIT (#4870)."""
        import build
        import scenario  # it imports gather: import it late
        import train
        g = self.bot.g
        tech = name == "up-research-status"
        if (sn := self.named(args[0], args[1], tech)) is None:
            return False
        if (n := self.game(sn, "tech", "age") if tech else self.game(sn, "unit", "building")) is None:
            return False
        if name == "up-pending-objects":
            return self.compare(args[2], self.count(n, total=True) - self.count(n), args[3])
        if name == "up-pending-placement":
            return n in self.unplaced
        if tech:                                                   # the AoE2 state; -1 (disabled) is unavailable
            return self.compare(args[2], max(scenario.tech_state(g, n), 0), RESEARCH_STATE.get(args[3], args[3]))
        return any(n in train.trains(g, home) and len(g.queues.get(rect, ())) < train.QUEUE
                   for rect, home in train.homes(g).items()) and not build.locked(g, n)

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

    def order(self, name, args):
        """The orders of the army and the buildings (#4876, airef): stop the attack, call the army home, stop units or
        queues, delete idle units or far farms. Each one uses the path of the player (stop, delete, cancel)."""
        import demolish
        import ruins
        import stance
        import train
        b = self.bot
        g, T = b.g, b.g.map.T
        if name == "up-reset-attack-now":                          # the flag of attack-now; the bot attacks no more
            self.attacking = False
        elif name == "up-retreat-now":                             # all soldiers, also the ones not in a wave
            b.wave = set(g.soldiers)
            b.retreat()
        elif name == "up-reset-unit":                              # (up-reset-unit TYPE UNIT): the Stop button
            n = (sn := self.named(args[0], args[1])) and self.game(sn, "unit")
            if n:
                n = n if isinstance(n, tuple) else (n,)
                units = sorted(u for u, m in g.soldiers.items() if m in n)
                for u in units:
                    g.command(f"aoe stop {u}")
                    vars(b).get("targets", {}).pop(u, None)
                    vars(b).get("wave", set()).discard(u)
                g.new_order(units)
                for v in [v for u, v in sorted(g.villagers.items()) if any(m.startswith("VILLAGER") for m in n)]:
                    g.new_order([v.uuid])
                    g.set(v, "idle")
        elif name == "up-reset-building":                          # (up-reset-building OPTION TYPE BUILDING)
            n = (sn := self.named(args[1], args[2])) and self.game(sn, "building")
            for rect in [r for r, m in sorted(train.homes(g).items()) if n and m in (n if isinstance(n, tuple) else (n,))]:
                gs = lambda: list(enumerate(train.groups(g.queues.get(rect, []))))   # noqa: E731
                while (i := next((i for i, e in reversed(gs()) if args[0] != 1 or e[0] not in train.TECHS), None)) \
                        is not None and train.cancel(g, b.nobody, rect, i):
                    pass                                           # option 1 keeps the research (airef)
        elif name == "up-delete-idle-units":                       # (up-delete-idle-units IDLE-TYPE)
            if (kind := self.game(args[0], "idle")) is None:     # airef IdleType: per_names.jsonl
                return
            kind = "VILLAGER" if kind.startswith("VILLAGER") else kind
            ships = vars(g).get("ships", {})
            trade = vars(g).get("trade", {})
            idle = sorted([u for u, v in g.villagers.items() if v.state == "idle"] if kind == "VILLAGER" else
                          [u for u, v in ships.items() if v.state == "idle" and getattr(v, "name", kind) == kind] +
                          [u for u, m in g.soldiers.items() if m.startswith(kind) and u not in trade])
            if idle:
                stance.delete_units(g, idle)
        elif name == "up-delete-distant-farms":                    # (up-delete-distant-farms TYPE VALUE): in tiles
            far = self.operand(args[0].rstrip(":"), args[1])
            cells = [c for d in g.map.drops["food"] for c in d]   # the mills and the town centers
            for rect in sorted(ruins.own(g).values()):
                mid = ((rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2)
                if far is not None and "FARM" in demolish.name(g, rect) and cells and \
                        min(math.dist(mid, c) for c in cells) / T > far:
                    demolish.fall(g, rect)

    def act(self, k, a):
        import build
        import train
        name, args, b = a[0], a[1:], self.bot
        g = b.g
        escrow = False
        if name in UP_QUEUE:                       # (up-train ESCROW TYPE UNIT), (up-build PLACE ESCROW TYPE BUILDING)
            if name == "up-build":
                if args[0] not in ("place-normal", "place-forward"):
                    self.warn("placement", args[0])
                name, args = ("build-forward" if args[0] == "place-forward" else "build"), args[1:]
            else:
                name = UP_QUEUE[name]
            escrow, sn = self.goals.get(args[0], 0) >= 1, self.named(args[1], args[2], name == "research")
            if sn is None:
                return
            args = (sn,)
        if name in ("train", "research"):
            n = self.game(args[0], "unit") if name == "train" else self.game(args[0], "tech", "age")
            if n and self.can("can-" + name, args[0], escrow):
                cost = train.price(g, n)
                if next((c for c in self.homes(n) if train.queue(g, b.nobody, c, n)), None) and escrow:
                    self.spend(cost)
        elif name in ("build", "build-forward"):
            n = self.game(args[0], "building")
            center = b.center() if name == "build" else self.forward()
            if n and self.can("can-build", args[0], escrow) and center and (rect := build.near(g, n, center)) is not None:
                cost = build.price(g, n)
                b.builder(build.found(g, n, rect))
                self.unplaced.discard(n)
                if escrow:
                    self.spend(cost)
            elif n and self.can("can-build", args[0], escrow):     # no free site yet: up-pending-placement
                self.unplaced.add(n)
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
        elif name in COST_ACTIONS:
            self.cost_action(name, args)
        elif name == "up-modify-goal":                               # (up-modify-goal GOAL OP VALUE)
            new = self.math(args[1], self.goals.get(args[0], -1), args[2])
            if new is not None:
                self.goals[args[0]] = new
        elif name == "up-get-indirect-goal":                         # (up-get-indirect-goal TYPE GOAL OUT)
            kind = self.type_kind(args[0])
            ref = self.operand(kind, args[1]) if kind else None
            if ref is not None:
                self.goals[args[2]] = self.goals.get(ref, -1)
        elif name in SHARED:                                         # (up-get-shared-goal TYPE ID GOAL), (up-set-signal
            self.shared(name, args)                                  # TYPE ID TYPE2 VALUE) ... (#4878)
        elif name == "up-set-indirect-goal":                         # (up-set-indirect-goal TYPE GOAL TYPE2 VALUE)
            kind, kind2 = self.type_kind(args[0]), self.type_kind(args[2])
            ref = self.operand(kind, args[1]) if kind else None
            value = self.operand(kind2, args[3]) if kind2 else None
            if ref is not None and value is not None:
                self.goals[ref] = value
        elif name == "up-modify-flag":                               # (up-modify-flag GOAL OP FLAG): the bits of a goal
            kind, _, rel = args[1].rpartition(":")
            if rel not in ("+", "-") or kind not in ("c", "g", "s"):
                return self.warn("operator", args[1])
            flag = self.operand(kind, args[2])
            if flag is not None:                                   # no flag yet: the goal has no bit
                value = self.goals.get(args[0], 0)
                self.goals[args[0]] = value | flag if rel == "+" else value & ~flag
        elif name == "up-assign-builders":                        # (up-assign-builders TYPE BUILDING TYPE2 VALUE)
            kind = self.type_kind(args[2])
            sn, value = self.named(args[0], args[1]), self.operand(kind, args[3]) if kind else None
            if sn is None or value is None or not (n := self.game(sn, "building")):
                return
            self.builders[n] = max(value, 1) if value != -1 else 1     # -1: the default of the game
            for site in [s for s in g.sites if s["name"] == n and not s.get("done")]:
                b.builder(site)                                        # more builders: the rest go at once (airef)
        elif name in ("up-retask-gatherers", "up-drop-resources"):    # (up-retask-gatherers RES TYPE VALUE)
            if args[0] not in STOCK:
                return self.warn("resource", args[0])
            if (value := self.typed(args[1], args[2])) is not None:
                (b.retask if name == "up-retask-gatherers" else b.drop)(args[0], value)
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
        elif name in ("up-buy-commodity", "up-sell-commodity"):          # (up-buy-commodity RES TYPE VALUE): VALUE trades
            import market
            buy = name == "up-buy-commodity"
            for _ in range(max(self.operand(args[1].rstrip(":"), args[2]) or 0, 0)):
                if not self.trade_ok(buy, args[0]) or not market.trade(g, b.nobody, args[0], buy):
                    break                                              # the first trade that fails stops the rest
        elif name == "up-tribute-to-player":                           # (up-tribute-to-player PLAYER RES TYPE VALUE)
            import diplomacy
            if args[1] not in STOCK:
                return self.warn("resource", args[1])
            for _ in range(max(self.operand(args[2].rstrip(":"), args[3]) or 0, 0) // diplomacy.LOT):
                if not diplomacy.send(g, b.nobody, args[0], args[1]):
                    break
        elif name == "up-modify-escrow":                               # (up-modify-escrow RES OP VALUE), as income()
            if args[0] not in STOCK:
                return self.warn("resource", args[0])
            if (new := self.math(args[1], self.escrow.get(args[0], 0), args[2])) is not None:
                if new := min(max(new, 0), g.stock[args[0]]):
                    self.escrow[args[0]] = new
                else:
                    self.escrow.pop(args[0], None)
        elif name == "up-release-escrow":
            self.escrow.clear()
        elif name == "attack-now":
            self.attacking = True
        elif name in ORDERS:
            self.order(name, args)
        elif name == "enable-timer":
            self.timers[args[0]] = b.time + args[1]
        elif name == "disable-timer":
            self.timers.pop(args[0], None)
        elif name == "up-set-timer":                               # (up-set-timer TYPE TIMER TYPE2 VALUE): -1 disables
            tid, value = self.typed(args[0], args[1]), self.typed(args[2], args[3])
            if tid is not None and value is not None:
                if value == -1:
                    self.timers.pop(tid, None)
                elif value > 0:
                    self.timers[tid] = b.time + value
        elif name == "up-get-timer":                               # (up-get-timer TYPE TIMER GOAL): due in ms; 0 if disabled
            tid = self.typed(args[0], args[1])
            if tid is not None:
                self.goals[args[2]] = round(self.timers.get(tid, 0) * 1000)
        elif name in ("up-get-victory-data", "up-get-victory-limit", "up-get-treaty-data"):
            self.victory_data(name, args)
        elif name == "set-stance":                                 # the path of the player menu; a locked team stays
            import diplomacy
            if g.data.get("unlock_teams") and args[1] in diplomacy.STANCES:
                for _ in diplomacy.STANCES:
                    if diplomacy.stance(g, args[0]) == args[1]:
                        break
                    diplomacy.change(g, None, args[0])
        elif name in ("chat-to-all", "chat-to-player", "up-chat-data-to-all", "up-chat-data-to-player"):
            to, args = ("@a", args) if name.endswith("all") else (f"@a[team=p{args[0]}]", args[1:])   # a seat: team pN
            text = args[0]
            if name.startswith("up-"):                              # (up-chat-data-to-all TEXT TYPE VALUE)
                kind = self.type_kind(args[1])
                if kind is None or (value := self.operand(kind, args[2])) is None:
                    return
                text = text.replace("%d", str(value)).replace("%s", self.text)
            who = self.name or f"Player {g.player}"
            g.command(f"tellraw {to} " + json.dumps({"text": f"<{who}> {text}"}))
        elif name in ("up-find-player", "up-find-next-player"):
            self.find_player(name, args)
        elif name == "up-change-name":
            self.name = str(args[0])
        elif name == "up-store-text":
            self.text = str(args[0])
        elif name == "up-store-player-name":                       # (up-store-player-name PLAYER)
            self.text = g.players.get(str(args[0]), {}).get("name") or f"Player {args[0]}"
        elif name == "up-store-map-name":                          # (up-store-map-name EXTENSION): no name gives ""
            self.text = str(g.data.get("map") or "")
        elif name in ("up-store-tech-name", "up-store-type-name"):  # (up-store-type-name TYPE ID): a script name
            value = self.typed(args[0], args[1])
            self.text = value if isinstance(value, str) else ""     # the game program has no table of the AoE2 ids
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
        elif name == "up-send-scout":                              # (up-send-scout GROUP-TYPE SCOUT-METHOD)
            self.send_scout(args[0], args[1])
        elif name == "up-reset-scouts":                            # the scouts stop (AoE2 Stop: aoe stop, new_order)
            for u in self.scouts:
                g.command(f"aoe stop {u}")
            g.new_order(self.scouts)
            self.scouts = []
        elif name in POINTS:
            self.points(name, args)
        elif name == "acknowledge-taunt":                            # (acknowledge-taunt PLAYER TAUNT)
            self.heard.discard((args[0], args[1]))
        elif name not in ("do-nothing", "chat-local-to-self", "enable-wall-placement", "up-chat-data-to-self",
                          "up-log-data", "up-request-hunters"):
            # no one sees a self chat; the bots have no hunt (#4739); each wall ring is always enabled (ring())
            self.warn("action", name)
