"""The game functions of an XS script (#5623, epic #5119): `host(g)` gives the `host` of `xs_run.Xs` for the side g (a
`gather.Gather`; the bots are `g.bots[i].g`, as in `scenario.attributes()`).

Minecraft feature: the scenario variables stay scores of `aoe_var` (the datapack triggers read them); the resources stay
in the stock of `Gather`. XS itself has no Minecraft feature (#5610). An unknown player or attribute gives one warning
line and 0, as an unknown name (`Xs.warn`), and the script goes on.
The unit ids (#5837): a start object keeps the reference ID of the scenario ("ref" of aoe2mc.json), so the IDs of the
editor in a script name the same objects; a new object takes the next ID above all start IDs, and an ID is never given
again (the model of record.Recorder). The map key -> ID is on the main Gather (`xs_ids`, `xs_top`: one ID space for all
sides), and the saved game keeps it (savegame.OPTIONAL). The keys are those of per.standing: a unit UUID, the building
target UUID. The state of a unit comes from its entity (Health, Pos) or the score aoe_hp of a building, not a copy.
"""
import json
import math
import os
import re
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402
import units  # noqa: E402
from buildings import COLOR_NAMES  # noqa: E402

DIPLOMACY = (0, 1, 3)                                                  # DiplomacyState: ally, neutral, enemy

POPULATION = {11: (lambda x: x.units, lambda x: x.soldiers),           # cAttributePopulation
              37: (lambda x: x.units,),                                # cAttributeCivilianPopulation
              40: (lambda x: x.soldiers,)}                             # cAttributeMilitaryPopulation
# cTechState* of xs-check: the state of a technology for xsGetTechState
INVALID, DISABLED, NOT_READY, READY, RESEARCHING, DONE, QUEUED = -2, -1, 0, 1, 2, 3, 4
SET_ATTRIBUTE, MOD_RESOURCE, ENABLE_OBJECT, MUL_RESOURCE = 0, 1, 2, 6   # the effect IDs of xsEffectAmount


def files(g, warn):
    """The file functions of XS (#5845): binary values (int, float 4 bytes; a string: its byte length and UTF-8; a
    vector: 3 floats) in the folder xs/ of the world, as the .xsdat files of the AoE2 profile folder. One file is open
    at a time. xsCreateFile writes the file of the script name; xsOpenFile reads a file by name."""
    import struct
    st = {"f": None}
    size = {0: 4, 1: 4, 3: 12}                                       # cOffsetInteger, cOffsetFloat, cOffsetVector

    def path(name):
        world = getattr(getattr(g, "game", None), "world", None)
        if not world or not name or "/" in name or "\\" in name or ".." in name:
            warn("file", name)
            return None
        os.makedirs(os.path.join(world, "xs"), exist_ok=True)
        return os.path.join(world, "xs", name + ".xsdat")

    def script():
        return os.path.splitext(os.path.basename((g.data.get("xs_script") or ["script"])[0]))[0]

    def close():
        if st["f"]:
            st["f"].close()
        st["f"] = None
        return True

    def open_(name, mode):
        close()
        if not (p := path(name)) or (mode == "rb" and not os.path.exists(p)):
            return False
        st["f"] = open(p, mode)
        return True

    def write(fmt, *v):
        if not st["f"] or st["f"].mode == "rb":
            return False
        st["f"].write(struct.pack(fmt, *v))
        return True

    def read(fmt, default):
        if not st["f"] or st["f"].mode != "rb" or len(b := st["f"].read(struct.calcsize(fmt))) < struct.calcsize(fmt):
            return default
        return struct.unpack(fmt, b)

    def read_string():
        n = read("<i", (0,))[0]
        return st["f"].read(n).decode("utf-8", "replace") if n > 0 else ""

    def offset(kind=-1, forward=False):
        if not st["f"] or not forward:                               # back over a string: its length is not known
            return False
        if int(kind) == 2:
            read_string()
        elif int(kind) in size:
            st["f"].seek(size[int(kind)], 1)
        else:
            return False
        return True

    def seek(at=-1):
        if not st["f"] or int(at) < 0:
            return False
        st["f"].seek(int(at))
        return True

    def file_size():
        return os.fstat(st["f"].fileno()).st_size if st["f"] else -1

    def string(data=""):
        b = str(data).encode("utf-8")
        return write(f"<i{len(b)}s", len(b), b)

    return {"xsCloseFile": close,
            "xsCreateFile": lambda append=False: open_(script(), "ab" if append else "wb"),
            "xsGetFilePosition": lambda: st["f"].tell() if st["f"] else -1,
            "xsGetFileSize": file_size,
            "xsOffsetFilePosition": offset,
            "xsOpenFile": lambda name="": open_(name or script(), "rb"),
            "xsReadFloat": lambda: read("<f", (-1.0,))[0],
            "xsReadInt": lambda: read("<i", (-1,))[0],
            "xsReadString": lambda: read_string() if st["f"] and st["f"].mode == "rb" else "",
            "xsReadVector": lambda: tuple(read("<3f", (-1.0, -1.0, -1.0))),
            "xsSetFilePosition": seek,
            "xsWriteFloat": lambda data=-1.0: write("<f", float(data)),
            "xsWriteInt": lambda data=-1: write("<i", int(data)),
            "xsWriteString": string,
            "xsWriteVector": lambda data=(-1.0, -1.0, -1.0): write("<3f", *data)}


def civ_id(name):
    """The AoE2 civilization ID of a civilization key: its index in the enum of AoE2ScenarioParser (the .dat order,
    as tools/dat_compare.civ_ids), else 0."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return next((i for i, c in enumerate(Civilization) if c.name == name), 0)


def civ_title(civ):
    """The English name of a civilization key or ID ("BRITONS" or 1 -> "Britons"), else ""."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    names = [c.name for c in Civilization]
    key = names[civ] if isinstance(civ, int) and 0 <= civ < len(names) else civ if civ in names else ""
    return key.replace("_", " ").title()


def timer(g, hill=False):
    """(seconds left, player) of the victory timer that ends first: the wonders and the relics (as per.victory_data), or
    the King of the Hill monument (hill.py, on the Gather of player 1); (0, 0) with no timer."""
    import conquest  # conquest imports gather: import it late
    if hill:
        h = vars(conquest.main(g)).get("hill") or {}
        left = [(h["left"], h["owner"])] if h.get("owner") else []
    else:
        left = [(t["left"], t["player"]) for t in vars(g).get("wonders", {}).values()]
        left += [(t["left"], t["player"])] if (t := vars(g).get("relic_timer")) else []
    time, player = min(left, default=(0, 0))
    return max(math.ceil(time), 0), int(player)


def ids(g):
    """{key: XS id} of the objects of g, made at the first call (the start objects of aoe2mc.json, the module doc)."""
    import combat
    if "xs_ids" not in vars(g):
        objs = g.data.get("objects", [])
        keys = [(combat.target_uuid(o["footprint"]) if o["kind"] == "building" and "footprint" in o else o.get("uuid"),
                 o.get("ref")) for o in objs]
        g.xs_ids = {k: ref for k, ref in keys if k and ref is not None}
        g.xs_top = max((o.get("ref") or 0 for o in objs), default=0)
        for k, ref in keys:
            if k and ref is None and k not in g.xs_ids:
                g.xs_top += 1
                g.xs_ids[k] = g.xs_top
    return g.xs_ids


def objects(g):
    """[(XS id, Gather, key, game name)] of the standing objects of all sides; a new object gets the next id."""
    import per
    known, out = ids(g), []
    for x in [g, *(b.g for b in getattr(g, "bots", ()))]:
        names = {u["uuid"]: u["name"] for u in x.units if "uuid" in u}
        for key, name, _ in per.standing(x):
            if key not in known:
                g.xs_top += 1
                known[key] = g.xs_top
            out.append((known[key], x, key, names.get(key, name)))
    return out


def timers(g):
    """Each game second: the boss bars of the XS timers (xsDisplayTimer) show the time left; a bar at 0 goes away."""
    import recap
    for n, t in list(vars(g).get("xs_timers", {}).items()):
        left = t["end"] - recap.game_time(g)
        bar = f"aoe2mc:xs_timer{n}"
        if left <= 0:
            g.command(f"bossbar remove {bar}")
            del g.xs_timers[n]
            continue
        sec = math.ceil(left)
        per = aoe2mc.TIME_UNITS.get(t["unit"], 1)
        shown = f"{sec // 60}:{sec % 60:02d}" if t["unit"] == 3 else str(math.ceil(left / per))
        g.command(f"bossbar set {bar} value {sec}")
        g.command(f"bossbar set {bar} name " + json.dumps(t["msg"].replace("%d", shown), ensure_ascii=False))


def screen(g, warn, side, unit, by_key, into):
    """The chat, instruction, timer, sound and view functions of XS (#5844), with the commands of the trigger effects
    "Send Chat", "Display Instructions", "Display Timer", "Play Sound" and "Change View" (aoe2mc.chat_lines, ...).
    Player -1 or 0: all players. No form: the zoom, the color mood, xsGetString and xsSetChatToPlayer (docs/research/xs.md)."""
    import recap

    def to(player):
        return "@a" if int(player) <= 0 else f"@a[team=p{int(player)}]"

    def text(msg):
        return re.sub(r"<[^<>]*>", "", str(msg)).replace("\r", "").strip()

    def send_chat(msg="", player=-1, silent=False):
        if not (t := text(msg)):
            return False
        g.command(f"tellraw {to(player)} " + json.dumps({"text": t}, ensure_ascii=False))
        return True

    def instructions(msg="", time=-1, source=-1, icon=-1, panel=-1, tag=False, notify=False, sound="", player=-1):
        if not (t := text(msg)):
            return False
        ticks = 20 * (int(time) if int(time) > 0 else 10)               # AoE2 default: 10 s
        for c in [f"title {to(player)} times 10 {ticks} 20", f"title {to(player)} subtitle " +
                  json.dumps({"text": t}, ensure_ascii=False), f'title {to(player)} title ""']:
            g.command(c)
        if len(t) > aoe2mc.SUBTITLE_CHARS:                              # the client cuts a long subtitle (#5298)
            send_chat(t, player)
        return True

    def display_timer(n=-1, msg="", time=-1, unit=-1, reset=False, player=-1):
        unit, bar = int(unit) if int(unit) in aoe2mc.TIME_UNITS else 2, f"aoe2mc:xs_timer{int(n)}"
        old = vars(g).setdefault("xs_timers", {}).get(int(n))
        sec = max(int(time) * aoe2mc.TIME_UNITS[unit], 1)
        end = old["end"] if old and not reset else recap.game_time(g) + sec
        if not old or reset:
            for c in [f"bossbar remove {bar}", f'bossbar add {bar} ""', f"bossbar set {bar} max {sec}",
                      f"bossbar set {bar} players {to(player)}"]:
                g.command(c)
        g.xs_timers[int(n)] = dict(end=end, unit=unit, msg=text(msg) or "%d")
        timers(g)
        return True

    def clear_timer(n=-1, player=-1):
        if vars(g).get("xs_timers", {}).pop(int(n), None) is None:
            return False
        g.command(f"bossbar remove aoe2mc:xs_timer{int(n)}")
        return True

    def remaining(n=-1, unit=-1, player=-1):
        if (t := vars(g).get("xs_timers", {}).get(int(n))) is None:
            return 0.0
        return max(t["end"] - recap.game_time(g), 0.0) / aoe2mc.TIME_UNITS.get(int(unit), 1)

    def at(loc):
        bx, bz = int(loc[0] * g.map.T), int(loc[1] * g.map.T)
        return f"{bx + 0.5} {float(g.map.y(bx, bz))} {bz + 0.5}"

    def play_sound(name="", player=-1, loc=(-1.0, -1.0, -1.0), angle=-1.0, uid=-1, everyone=False):
        if not str(name):
            return False
        sound = next(s for part, s in aoe2mc.SOUNDS if part in str(name).upper())   # the last part "" fits all
        who = "@a" if everyone else to(player)
        if loc[0] >= 0 and loc[1] >= 0:
            g.command(f"playsound minecraft:{sound} master {who} {at(loc)}")
        elif int(uid) >= 0 and (u := unit(uid)):
            u[0].command(f"execute at {u[1]} run playsound minecraft:{sound} master {who} ~ ~ ~")
        else:
            g.command(f"execute as {who} at @s run playsound minecraft:{sound} master @s")
        return True

    def set_view(player=-1, loc=(-1.0, -1.0, -1.0), duration=-1):
        if loc[0] < 0 or loc[1] < 0:                                    # in Minecraft the player is the camera
            return False
        g.command(f"tp {to(player)} {at(loc)}")
        return True

    def view(player=-1):
        x = side(player)
        p = x and x.pos(getattr(x, "person", None) or x.who)
        return (p[0] / x.map.T, p[2] / x.map.T, 0.0) if p else (-1.0, -1.0, -1.0)

    def selected(r, a=-1, player=-1):
        x = side(player)
        return into(r, sorted(by_key(k) for k in (getattr(x, "selected", None) or ())) if x else [], a)
    selected.runtime = True

    def visible(uid=-1, fog=False, player=-1):
        import diplomacy
        import fog as fogs
        x, u = side(player), unit(uid)
        if not (x and u):
            return False
        if u[0] is x or diplomacy.stance(x, u[0].player) == "ally":
            return True
        return u[1] not in set(vars(x).get("fog", {}).get("hidden", ())) - fogs.seen(x)

    return {"xsClearInstructions": lambda panel=-1, player=-1: g.command(f"title {to(player)} clear") is not None,
            "xsClearTimer": clear_timer,
            "xsDisplayInstructions": instructions,
            "xsDisplayTimer": display_timer,
            "xsPlaySound": play_sound,
            "xsSendChat": send_chat,
            "xsSetViewPosition": set_view,
            "xsUnsyncGetLocalPlayerId": lambda: int(g.player),
            "xsUnsyncGetPlayerSelectedUnitIds": selected,
            "xsUnsyncGetTimerTimeRemaining": remaining,
            "xsUnsyncGetViewPosition": view,
            "xsUnsyncIsUnitVisible": visible}


def host(g):
    """{XS name: callable} of the game functions for the side g."""
    import recap  # recap imports gather: import it late
    import train
    warned = set()
    data = getattr(g, "data", None) or {}
    seed = zlib.crc32(f"{data.get('map_size')}-{len(data.get('objects', ()))}".encode())   # the map, not the clock
    rng = np.random.default_rng(seed)

    def warn(what, value):
        if (what, value) not in warned:
            warned.add((what, value))
            print(f"XS script: unknown {what} {value}: skipped", file=sys.stderr)

    def side(player):
        x = {s.player: s for s in [g, *(b.g for b in getattr(g, "bots", ()))]}.get(who(player))   # -1: the context
        if x is None:
            warn("player", player)
        return x

    def resource(attribute):
        if 0 <= int(attribute) < len(aoe2mc.STORES):
            return aoe2mc.STORES[int(attribute)]
        warn("attribute", attribute)

    def attribute(player, a):
        if int(a) in POPULATION:                                       # the units of the side, not a stock (#5807)
            x = side(player)
            return float(sum(len(f(x)) for f in POPULATION[int(a)])) if x else 0.0
        x, r = side(player), resource(a)
        return float(x.stock.get(r, 0)) if x and r else 0.0

    def set_attribute(player, a, value):
        x, r = side(player), resource(a)
        if x and r:
            x.stock[r] = max(int(value), 0)
            x.show_stock()                                             # the board shows the stock (#3111)

    def names(x):
        return [*(o["name"] for o in x.units), *x.soldiers.values(), *train.owned(x)]

    def count(player, unit, total=False):
        if (x := side(player)) is None:
            return 0
        name = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        more = [s["name"] for s in x.sites if not s.get("done") and s["player"] == x.player] + \
            [e["name"] for q in x.queues.values() for e in q] if total else []
        return sum(n == name for n in names(x) + more)

    def variable(n):
        m = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #v{int(n)} aoe_var") or "")
        return int(m[1]) if m else 0

    def set_variable(n, value):
        g.command(f"scoreboard players set #v{int(n)} aoe_var {int(value)}")

    def civilization(player):
        import civs  # civs imports gather: import it late
        return civ_id(civs.real(g, player)) if side(player) else 0

    def techs(player):
        return len(x.techs) if (x := side(player)) else 0

    def size():
        return int(data.get("map_size") or 0)

    def tile(x, y, a):
        rows = data.get({0: "terrain", 1: "elevation"}.get(int(a), ""))   # 0: terrain, 1: elevation (a choice)
        if rows is None:
            warn("tile attribute", a)
            return -1
        if not (0 <= int(y) < len(rows) and 0 <= int(x) < len(row := rows[int(y)].split())):
            return -1
        return int(row[int(x)])

    def who(player=-1):
        c = ctx[0] if ctx[0] is not None else g.player                 # no context: the side of the script
        return c if int(player) == -1 else int(player)

    def player_data(player):
        return data.get("players", {}).get(str(who(player)))

    def map_name(extension=False):
        lobby = data.get("lobby", {})
        name = lobby.get("scenario") or lobby.get("script") or ""
        return name if extension else os.path.splitext(name)[0]

    def in_game(player):
        x = side(player)
        return bool(x) and not getattr(x, "lost", False)

    def color(n):
        return COLOR_NAMES[n - 1] if isinstance(n, int) and 1 <= n <= len(COLOR_NAMES) else None

    def row(player):
        return g.players.get(str(int(player))) if side(player) else None

    def stance(a, b):
        """The DiplomacyState of player a to player b (ALLY 0, NEUTRAL 1, ENEMY 3), as diplomacy.stance."""
        import gather
        if row(a) is None or row(b) is None:
            return -1
        return 0 if gather.allied(g.players, int(a), int(b)) else 1 if int(b) in row(a).get("neutral", ()) else 3

    def set_diplomacy(a, b, kind, mirror=False):
        """As "Change Diplomacy" (aoe2mc.diplomacy_lines): the score of aoe_dip, and scenario.diplomacy applies it."""
        a, b, kind = int(a), int(b), int(kind)
        if row(a) is None or row(b) is None or a == b or kind not in DIPLOMACY:
            return False
        for n, m in ((a, b), (b, a))[:1 + bool(mirror)]:
            g.command(f"scoreboard players set #p{n}.p{m} aoe_dip {kind + 1}")
        g.command("scoreboard players set #any aoe_dip 1")
        return True

    def declare_victory(player, victory=False):
        """As "Declare Victory" (aoe2mc.victory_lines): the score #p<N> of aoe_win, and scenario.victory ends the game.
        A defeat (victory false) has no form: one warning line."""
        if not victory:
            warn("defeat of player", player)
        elif side(player):
            g.command(f"scoreboard players set #p{int(player)} aoe_win 1")

    def set_name(player, key, name):
        if (r := row(player)) is None:
            return False
        r[key] = str(name)
        if key == "name":                                              # the team shows the name (Minecraft feature)
            g.command(f"team modify p{int(player)} displayName " + json.dumps(str(name)))
        return True

    def set_color(player, n):
        """As "Change Player Color" (aoe2mc.color_lines): the team color."""
        if (r := row(player)) is None or color(int(n)) is None:
            return False
        r["color"] = color(int(n))
        g.command(f"team modify p{int(player)} color {units.TEAM_COLOR[r['color']]}")
        return True

    def player_civ_name(player, localized=False):
        return (r.get("civ_name") or civ_title(r.get("civ", ""))) if (r := row(player)) else ""

    def color_tag(player):
        return f"<{r.get('color', '').upper()}>" if (r := row(player)) else ""

    def victory():
        from AoE2ScenarioParser.datasets.trigger_lists import SecondaryGameMode, VictoryCondition
        win = g.data.get("victory") or {}
        key = win.get("condition", "standard").upper().replace("-", "_")
        modes = sum(m.value for m in SecondaryGameMode if m.name.lower().replace("_", "-") in win.get("modes", ()))
        return (VictoryCondition[key].value if key in VictoryCondition.__members__ else 0), modes

    def victory_type():
        import per  # per imports gather: import it late
        return per.VICTORY_TYPES.get(getattr(g, "victory", "standard"), 0)

    def tech(t):
        n = aoe2mc.tech_names().get(int(t))
        if n not in train.TECHS:
            warn("technology", t)
            return None
        return n

    def tech_state(t, player):
        import civs  # civs imports gather: import it late
        n, x = tech(t), side(player)
        if n is None or x is None:
            return INVALID
        if train.researched(x, n):
            return DONE
        if (q := next((q for q in x.queues.values() if any(e["name"] == n for e in q)), None)) is not None:
            return RESEARCHING if q[0]["name"] == n else QUEUED
        if civs.missing(x, n):
            return DISABLED
        return READY if train.unlocked(x, n) else NOT_READY

    def research_tech(t, force=False, available=False, player=-1):
        """As the trigger effect "Research Technology" (scenario.research): at no cost, now. Without force only a
        technology of the state READY (or NOT_READY with techAvailable)."""
        state = tech_state(t, player)
        if state in (INVALID, DONE) or not force and state not in (READY, *(NOT_READY,) * bool(available)):
            return False
        train.research(side(player), {"name": tech(t), "player": "@a"}, start=True)
        return True

    def tech_name(t, player=-1, internal=False):
        from AoE2ScenarioParser.datasets.techs import TechInfo
        if internal:
            return next((i.name for i in TechInfo if i.ID == int(t)), "")
        if (n := tech(t)) is None:
            return ""
        x = side(player) if int(player) > 0 else None
        return vars(x).get("trigger_names", {}).get(n) if x and n in vars(x).get("trigger_names", {}) else \
            train.ITEMS.get(n, (None, None, None))[2] or units.pretty(n)

    def set_tech_name(t, player, text):
        if (n := tech(t)) and (x := side(player)):                 # the menus show it (train.show, #2821)
            vars(x).setdefault("trigger_names", {})[n] = str(text)

    def object_key(unit):
        n = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        if n is None:
            warn("object", unit)
        return n

    def available(unit, player):
        n, x = object_key(unit), side(player)
        return bool(n and x and train.unlocked(x, n))

    def effect(e, o, a, value, player=-1, train_location=-1):
        """cModResource (a = cAttributeSet or cAttributeAdd), cMulResource and cEnableObject (as the trigger effect
        "Enable/Disable Object", g.trigger_menus). The unit attributes of the .dat have no table in the game program:
        one warning line."""
        x = side(player)
        if x is None:
            return
        if int(e) in (MOD_RESOURCE, MUL_RESOURCE) and (r := resource(o)):
            old = x.stock.get(r, 0)
            x.stock[r] = max(int(old * value if int(e) == MUL_RESOURCE else value + old * (int(a) == 1)), 0)
            x.show_stock()
        elif int(e) == ENABLE_OBJECT and (n := object_key(o)):
            vars(x).setdefault("trigger_menus", {})[n] = bool(int(a))
        elif int(e) not in (MOD_RESOURCE, MUL_RESOURCE, ENABLE_OBJECT):
            warn("effect", e)

    def unit(uid):
        """(Gather, key, game name) of the unit id, or None with one warning."""
        hit = next(((x, k, n) for i, x, k, n in objects(g) if i == int(uid)), None)
        if hit is None:
            warn("unit", uid)
        return hit

    def type_id(uid):
        import record
        return record.types().get(u[2], -1) if (u := unit(uid)) else -1

    def hitpoints(uid):
        if (u := unit(uid)) is None:
            return -1.0
        x, key, _ = u
        if key in getattr(x, "forts", ()):                             # a building: its score (bot.hp)
            m = re.search(r" has (-?\d+) ", x.command(f"scoreboard players get {key} aoe_hp") or "")
        else:
            import gather
            m = re.search(gather.NUMBER, (x.command(f"data get entity {key} Health") or "").rsplit(":", 1)[-1])
        return float(m[1]) if m else -1.0

    def position(uid):
        """The tiles (x, y) of the unit and 0: the units walk on the ground (per "point-z")."""
        if (u := unit(uid)) and (p := u[0].positions([u[1]]).get(u[1])) is not None:
            return (p[0] / u[0].map.T, p[2] / u[0].map.T, 0.0)
        return (-1.0, -1.0, -1.0)

    def held(uid, a):
        v = u[0].villagers.get(u[1]) if (u := unit(uid)) else None
        return float(v.load) if v and v.load and 0 <= int(a) < len(aoe2mc.STORES) and aoe2mc.STORES[int(a)] == v.res \
            else 0.0

    def civ_name(uid, localized=False):
        import civs
        return (civs.real(g, u[0].player) or "").replace("_", " ").title() if (u := unit(uid)) else ""

    def unit_name(uid, internal=False):
        if (u := unit(uid)) is None:
            return ""
        return u[2] if internal else u[2].replace("_", " ").capitalize()

    def unit_class(uid):
        import per
        return per.klass(u[2]) if (u := unit(uid)) else -1

    def kind(player, unit):
        """The side and the AoE2 name of object ID unit, or (None, None) with one warning line."""
        name = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        if name is None:
            warn("object", unit)
        return side(player), name

    def object_attribute(player=-1, unit=-1, a=-1, damage=-1):
        """A combat value of the unit type of the player (train.stats, with the trigger changes), as "Modify
        Variable by Attribute" (scenario.reads): the attributes of aoe2mc.STAT_ATTRIBUTES and CLASS_ATTRIBUTES."""
        import combat  # combat imports gather: import it late
        x, name = kind(player, unit)
        field = aoe2mc.STAT_ATTRIBUTES.get(int(a)) or aoe2mc.CLASS_ATTRIBUTES.get((int(a), int(damage)))
        if field is None:
            warn("object attribute", (a, damage))
        if not (x and name and field and name in combat.STATS):
            return 0.0
        return float(getattr(train.stats(x, name), field))

    def object_class(player=-1, unit=-1):
        """The first ObjectClass whose test of train.CLASSES holds for the unit type, else -1."""
        from AoE2ScenarioParser.datasets.trigger_lists import ObjectClass
        _, name = kind(player, unit)
        return next((c.value for c in ObjectClass if name and train.applies(f"@{c.name.lower()}", name)), -1)

    def object_type(player=-1, unit=-1):
        """The ObjectType: 2 building, 3 villager, 4 a unit with combat values, else 1 (other)."""
        import combat  # combat imports gather: import it late
        prefix, name = aoe2mc.object_kinds().get(int(unit), (None, None))
        if name is None:
            warn("object", unit)
            return -1
        return 2 if prefix == "B" else 3 if name.startswith("VILLAGER") else 4 if name in combat.STATS else 1

    def object_name(unit=-1, player=-1, internal=False):
        name = kind(player, unit)[1] if int(player) > 0 else aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        return (name if internal else name.replace("_", " ").title()) if name else ""

    def enum_name(enum):
        """The name of an enum member of AoE2ScenarioParser by its ID: "" for an unknown ID."""
        def get(i=-1, localized=False):
            from AoE2ScenarioParser.datasets import trigger_lists
            e = getattr(trigger_lists, enum)
            n = e(int(i)).name if int(i) in set(e) else ""
            return n.replace("_", " ").title() if localized else n
        return get

    def by_key(key):
        """The XS id of the object key (also a Gaia start object), or -1."""
        objects(g)
        return ids(g).get(key, -1)

    def rect_key(rect):
        """The key of the building with the block rect (x0, x1, z0, z1) of garrisons, rally points and sites."""
        import combat
        return combat.target_uuid([rect[i] for i in (0, 2, 1, 3)])

    def rect_of(x, key):
        """The rect of the building key of side x in its garrisons or rally points, or None."""
        return next((r for r in [*getattr(x, "garrisons", {}), *getattr(x, "rally", {})] if rect_key(r) == key), None)

    def into(r, values, a):
        """The int array a of the runtime r with values (a < 0: a new array): its id (#5838)."""
        if int(a) < 0:
            a = r.array_create("int", 0, -1, "")
        if r.array_resize("int", int(a), len(values)):
            for n, v in enumerate(values):
                r.array_set("int", int(a), n, v)
            return int(a)
        return -1

    def garrisoned_in(uid):
        if (u := unit(uid)) is None:
            return -1
        rect = next((r for r, us in getattr(u[0], "garrisons", {}).items() if u[1] in us), None)
        return by_key(rect_key(rect)) if rect else -1

    def garrisoned_ids(r, uid):
        u = unit(uid)
        rect = u and rect_of(u[0], u[1])
        return into(r, sorted(by_key(k) for k in u[0].garrisons.get(rect, ())) if rect else [], -1)
    garrisoned_ids.runtime = True

    def player_unit_ids(r, player=-1, kind=-1, a=-1):
        """The ids of the objects of the player of object type or ObjectClass kind (-1: all) in array a (-1: a new one)."""
        import per
        import record
        x, types = side(player), record.types()
        out = [i for i, y, _, n in objects(g) if y is x and (int(kind) < 0 or types.get(n) == int(kind)
                                                             or per.klass(n) == int(kind))]
        return into(r, out, a)
    player_unit_ids.runtime = True

    def unit_attribute(uid, a=-1, damage=-1):
        import combat
        field = aoe2mc.STAT_ATTRIBUTES.get(int(a)) or aoe2mc.CLASS_ATTRIBUTES.get((int(a), int(damage)))
        if field is None:
            warn("unit attribute", (a, damage))
        if not ((u := unit(uid)) and field and u[2] in combat.STATS):
            return 0.0
        return float(getattr(train.stats(u[0], u[2], u[1]), field))

    def build_points(uid):
        """The progress (0 to 1) of the construction site of the building; 1 for a complete building."""
        if (u := unit(uid)) is None:
            return -1.0
        site = next((s for s in u[0].sites if rect_key(s["footprint"]) == u[1]), None)
        return float(site["progress"]) if site else 1.0

    def gather_point(uid):
        """The rally point of the building in tiles, or (-1, -1, -1)."""
        u = unit(uid)
        rect = u and rect_of(u[0], u[1])
        if rect and rect in getattr(u[0], "rally", {}):
            x, z = u[0].rally[rect][0]
            return ((x + 0.5) / u[0].map.T, (z + 0.5) / u[0].map.T, 0.0)
        return (-1.0, -1.0, -1.0)

    def move_target(uid):
        """The walk goal of a villager in tiles, or (-1, -1, -1)."""
        v = u[0].villagers.get(u[1]) if (u := unit(uid)) else None
        if v is not None and v.goal:
            return ((v.goal[0] + 0.5) / u[0].map.T, (v.goal[1] + 0.5) / u[0].map.T, 0.0)
        return (-1.0, -1.0, -1.0)

    def target_id(uid):
        """The id of the attack target of a soldier of a bot, or the prey of a villager; -1 for none."""
        if (u := unit(uid)) is None:
            return -1
        x, key = u[0], u[1]
        v = x.villagers.get(key)
        bot = next((b for b in getattr(g, "bots", ()) if b.g is x), None)
        t = v.prey if v is not None else vars(bot).get("targets", {}).get(key) if bot else None
        return by_key(t) if t else -1

    def type_kind(uid):
        """The ObjectType of the unit (as xsGetObjectType)."""
        import record
        return object_type(-1, record.types().get(u[2], -1)) if (u := unit(uid)) else -1

    def rect_any(x, key):
        """The rect (x0, x1, z0, z1) of the building key of side x: its garrisons, rally points, sites or start data."""
        rects = [*getattr(x, "garrisons", {}), *getattr(x, "rally", {}), *(tuple(s["footprint"]) for s in x.sites)]
        rects += [(f[0], f[2], f[1], f[3]) for o in x.data.get("objects", ()) if (f := o.get("footprint"))]
        return next((r for r in rects if rect_key(r) == key), None)

    def block(x, loc):
        """The block position (x, y, z) of the tile vector loc (the middle of the tile, on the ground)."""
        bx, bz = int(loc[0] * x.map.T), int(loc[1] * x.map.T)
        return bx + 0.5, float(x.map.y(bx, bz)), bz + 0.5

    def create(o=-1, player=-1, loc=(-1.0, -1.0, -1.0), foundation=False, sound=False, collision=False):
        """As "Create Object" (train.summon; a building: scenario.foundation, complete without foundation). The id of
        the new object, or -1."""
        import scenario
        x, name = kind(player, o)
        if not (x and name) or loc[0] < 0 or loc[1] < 0:
            return -1
        before = {i for i, *_ in objects(g)}
        if aoe2mc.object_kinds()[int(o)][0] == "B":
            scenario.foundation(g, x.player, name, (int(loc[0]), int(loc[1])), done=not foundation)
        elif train.summon(x, name, block(x, loc)) is None:
            return -1
        return max({i for i, *_ in objects(g)} - before, default=-1)

    def unit_do(f):
        """f(Gather, key, name) for the unit id, True; False for an unknown id (one warning)."""
        def call(uid=-1, *a):
            if (u := unit(uid)) is None:
                return False
            return f(*u, *a) is not False
        return call

    def remove(x, key, name):
        if key in getattr(x, "forts", ()):                             # a building is blocks: no kill
            return warn("removal of building", key) or False
        x.command(f"kill {key}")                                       # the Gather drops a dead unit

    def set_hp(x, key, name, value=-1.0):
        if key in getattr(x, "forts", ()):
            x.command(f"scoreboard players set {key} aoe_hp {max(int(value), 0)}")
        else:
            x.command(f"data modify entity {key} Health set value {max(float(value), 0.0)}f")

    def set_owner(x, key, name, player=-1, flash=False):
        import owners  # owners imports gather: import it late
        if row(player) is None or key in getattr(x, "forts", ()):
            return False
        owners.give(g, key, int(player))
        x.command(f"team join p{int(player)} {key}")                   # the team color (as "Change Ownership")

    def set_position(x, key, name, loc=(-1.0, -1.0, -1.0), collision=False):
        if key in getattr(x, "forts", ()) or loc[0] < 0:
            return False
        x.command("tp {} {} {} {}".format(key, *block(x, loc)))

    def name_unit(x, key, name, text=""):
        x.command(f"data modify entity {key} CustomName set value " + json.dumps(str(text)))

    def flash(x, key, name, player=-1, sound=-1):
        x.command(f"effect give {key} minecraft:glowing 2 0 true")     # the Minecraft outline as the AoE2 flash

    def stop(x, key, name):
        import ai
        if (p := x.positions([key]).get(key)) is None:
            return False
        ai.move(x, key, name, x.map.T, *p)                             # a walk to its own place ends its order

    def set_held(x, key, name, value=-1.0, a=-1):
        v = x.villagers.get(key)
        if v is None or not 0 <= int(a) < len(aoe2mc.STORES):
            return False
        v.res, v.load = aoe2mc.STORES[int(a)], max(int(value), 0)

    def set_build_points(x, key, name, value=-1.0):
        site = next((s for s in x.sites if rect_key(s["footprint"]) == key), None)
        if site is None:
            return False
        site["progress"] = min(max(float(value), 0.0), 1.0)

    def set_gather_point(x, key, name, loc=(-1.0, -1.0, -1.0), target=-1):
        if (rect := rect_any(x, key)) is None or loc[0] < 0:
            return False
        train.rally(x, rect, (int(loc[0] * x.map.T), int(loc[1] * x.map.T)))

    def task_units(uid=-1, action=-1, loc=(-1.0, -1.0, -1.0), target=-1, *more):
        """A move to loc, or an attack of the unit target (as "Task Object": `aoe moveto`, `aoe attack`)."""
        import ai
        if (u := unit(uid)) is None:
            return False
        x, key, name = u
        if int(target) >= 0:
            t = unit(target)
            return bool(t) and bool(ai.attack(x, [key], [name], x.map.T, t[1]) or True)
        if loc[0] < 0:
            return False
        ai.move(x, key, name, x.map.T, *block(x, loc))
        return True

    def train_object(building=-1, o=-1, n=-1):
        """Queue n units o at the building (train.queue, with its cost, as a click of the player)."""
        u, name = unit(building), object_key(o)
        rect = u and rect_any(u[0], u[1])
        if not (rect and name):
            return False
        return sum(bool(train.queue(u[0], u[0].player, (rect[0], rect[2]), name)) for _ in range(max(int(n), 1))) > 0

    task = {}

    def task_amount(field=-1, value=-1.0):
        task[int(field)] = float(value)

    ctx = [None]                                                       # xsSetContextPlayer; None: the first AI script

    def script():
        """The AI script (per.Script) of the context player: the XS functions of the AI act on it (#5846)."""
        bots = [b for b in getattr(g, "bots", ()) if getattr(b, "script", None)]
        b = next((b for b in bots if ctx[0] is None or b.g.player == ctx[0]), None)
        if b is None:
            warn("AI script of player", ctx[0])
        return b and b.script

    def get(what, n, default=0):
        if (s := script()) is None:
            return default
        if what == "goal":
            return int(s.goals.get(int(n), 0 if 1 <= int(n) <= 512 else -1))
        if what == "sn":
            import per
            if (name := per.SN_IDS.get(int(n))) is None:
                return warn("strategic number", n) or default
            return int(s.number(name))
        return s.table(what).get(int(n), 0)                            # "signal"; "event": the AI script goal

    def put(what, n, value):
        if (s := script()) is None:
            return
        if what == "goal":
            s.goals[int(n)] = int(value)
        elif what == "sn":
            import per
            if (name := per.SN_IDS.get(int(n))) is None:
                return warn("strategic number", n)
            s.sn[name] = int(value)
        else:
            s.table(what)[int(n)] = int(value)

    def set_context(player):
        ctx[0] = int(player)

    return {**files(g, warn), **screen(g, warn, side, unit, by_key, into), "xsCreateUnit": create, "xsDeclareVictory": declare_victory,
            "xsDoesUnitExist": lambda uid: any(i == int(uid) for i, *_ in objects(g)),
            "xsEffectAmount": effect,
            "xsFlashUnit": unit_do(flash),
            "xsGetAiScriptGoal": lambda n=-1: bool(get("event", n)),
            "xsGetAiSignal": lambda n=-1, legacy=False: get("signal", n),
            "xsGetCivName": lambda civ, localized=False: civ_title(int(civ)),
            "xsGetContextPlayer": lambda: -1 if ctx[0] is None else ctx[0],
            "xsGetDamageClassName": enum_name("DamageClass"),
            "xsGetDiplomacy": stance,
            "xsGetGarrisonedInUnitId": garrisoned_in,
            "xsGetGarrisonedUnitIds": garrisoned_ids,
            "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetGoal": lambda n=-1: get("goal", n, -1),
            "xsGetHandicapMultiplier": lambda player=-1: 1.0,           # the game program has no handicap
            "xsGetMapHeight": size,
            "xsGetMapName": map_name,
            "xsGetMapSeed": lambda: int(seed & 0x7FFFFFFF),
            "xsGetMapTileAttribute": tile,
            "xsGetMapWidth": size,
            "xsGetNumPlayers": lambda: len(data.get("players", {})) + 1,   # with gaia, as AoE2
            "xsGetObjectAttribute": object_attribute,
            "xsGetObjectAttributeName": enum_name("ObjectAttribute"),
            "xsGetObjectClass": object_class,
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetObjectName": object_name,
            "xsGetObjectType": object_type,
            "xsGetPlayerAttributeName": enum_name("Attribute"),
            "xsGetPlayerCivName": player_civ_name,
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerColorTag": color_tag,
            "xsGetPlayerInGame": in_game,
            "xsGetPlayerName": lambda player=-1: (player_data(player) or {}).get("name", f"Player {who(player)}"),
            "xsGetPlayerNumberOfObjects": lambda player: sum(x is side(player) for _, x, _, _ in objects(g)),
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetPlayerUnitIds": player_unit_ids,
            "xsGetRandomNumber": lambda: int(rng.integers(0, 32768)),
            "xsGetRandomNumberLH": lambda low, high: int(rng.integers(int(low), max(int(high), int(low) + 1))),
            "xsGetRandomNumberMax": lambda m: int(rng.integers(0, max(int(m), 1))),
            "xsGetStrategicNumber": lambda n=-1: get("sn", n, -1),
            "xsGetTaskAmount": lambda field=-1: task.get(int(field), 0.0),
            "xsGetTechName": tech_name,
            "xsGetTechState": tech_state,
            "xsGetTurn": lambda: int(recap.game_time(g) * 20),          # one turn per Minecraft tick (a choice)
            "xsGetUnitAttribute": unit_attribute,
            "xsGetUnitAttributeHeld": held,
            "xsGetUnitBuildPoints": build_points,
            "xsGetUnitCaption": lambda uid: unit_name(uid),             # no own captions: the unit name
            "xsGetUnitCivName": civ_name,
            "xsGetUnitClass": unit_class,
            "xsGetUnitCopyId": type_id,
            "xsGetUnitGatherPoint": gather_point,
            "xsGetUnitHitpoints": hitpoints,
            "xsGetUnitName": unit_name,
            "xsGetUnitMoveTarget": move_target,
            "xsGetUnitObjectId": type_id,
            "xsGetUnitOwner": lambda uid: u[0].player if (u := unit(uid)) else -1,
            "xsGetUnitPlayerName": lambda uid: (player_data(u[0].player) or {}).get("name", f"Player {u[0].player}")
            if (u := unit(uid)) else "",
            "xsGetUnitPosition": position,
            "xsGetUnitTargetUnitId": target_id,
            "xsGetUnitType": type_kind,
            "xsGetVictoryCondition": lambda: victory()[0],
            "xsGetVictoryConditionForSecondaryGameMode": lambda: victory()[1],
            "xsGetVictoryPlayer": lambda: timer(g)[1],
            "xsGetVictoryPlayerForSecondaryGameMode": lambda: timer(g, True)[1],
            "xsGetVictoryTime": lambda: timer(g)[0],
            "xsGetVictoryTimeForSecondaryGameMode": lambda: timer(g, True)[0],
            "xsGetVictoryType": victory_type,
            "xsGetWorldPlayerId": who,
            "xsGetWorldTime": lambda: int(recap.game_time(g) * 1000),   # milliseconds
            "xsIsObjectAvailable": available,
            "xsIsObjectValid": lambda oid, player=-1: int(oid) in aoe2mc.object_kinds(),
            "xsPlayerAttribute": attribute,
            "xsRemoveUnit": unit_do(remove),
            "xsResearchTechnology": research_tech,
            "xsResetTaskAmount": task.clear,
            "xsSetAiScriptGoal": lambda n=-1, v=False: put("event", n, bool(v)) or True,
            "xsSetAiSignal": lambda n=-1, v=-1, legacy=False: put("signal", n, v),
            "xsSetContextPlayer": set_context,
            "xsSetDiplomacy": set_diplomacy,
            "xsSetGoal": lambda n=-1, v=-1: put("goal", n, v),
            "xsSetPlayerAttribute": set_attribute,
            "xsSetPlayerCivName": lambda player, name="": set_name(player, "civ_name", name),
            "xsSetPlayerColor": set_color,
            "xsSetPlayerName": lambda player, name="": set_name(player, "name", name),
            "xsSetStrategicNumber": lambda n=-1, v=-1: put("sn", n, v),
            "xsSetTechName": set_tech_name,
            "xsSetTriggerVariable": set_variable,
            "xsSetUnitAttributeHeld": unit_do(set_held),
            "xsSetUnitBuildPoints": unit_do(set_build_points),
            "xsSetUnitCaption": unit_do(name_unit),
            "xsSetUnitGatherPoint": unit_do(set_gather_point),
            "xsSetUnitHitpoints": unit_do(set_hp),
            "xsSetUnitName": unit_do(name_unit),
            "xsSetUnitOwner": unit_do(set_owner),
            "xsSetUnitPosition": unit_do(set_position),
            "xsStopUnit": unit_do(stop),
            "xsTaskAmount": task_amount,
            "xsTaskUnits": task_units,
            "xsTrainObject": train_object,
            "xsTriggerVariable": variable}
