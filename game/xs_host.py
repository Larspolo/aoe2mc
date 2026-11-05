"""The game functions of an XS script (#5623, epic #5119): `host(g)` gives the `host` of `xs_run.Xs` for the side g (a
`gather.Gather`; the bots are `g.bots[i].g`, as in `scenario.attributes()`).

Minecraft feature: the scenario variables stay scores of `aoe_var` (the datapack triggers read them); the resources stay
in the stock of `Gather`. XS itself has no Minecraft feature (#5610). An unknown player or attribute gives one warning
line and 0, as an unknown name (`Xs.warn`), and the script goes on.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402

POPULATION = {11: (lambda x: x.units, lambda x: x.soldiers),           # cAttributePopulation
              37: (lambda x: x.units,),                                # cAttributeCivilianPopulation
              40: (lambda x: x.soldiers,)}                             # cAttributeMilitaryPopulation


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


def host(g):
    """{XS name: callable} of the game functions for the side g."""
    import recap  # recap imports gather: import it late
    import train
    warned = set()

    def warn(what, value):
        if (what, value) not in warned:
            warned.add((what, value))
            print(f"XS script: unknown {what} {value}: skipped", file=sys.stderr)

    def side(player):
        x = {s.player: s for s in [g, *(b.g for b in getattr(g, "bots", ()))]}.get(int(player))
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

    f = files(g, warn)
    return {**f, "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerNumberOfTechs": techs,
            "xsPlayerAttribute": attribute,
            "xsSetPlayerAttribute": set_attribute,
            "xsSetTriggerVariable": set_variable,
            "xsTriggerVariable": variable}
