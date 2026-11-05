"""The game functions of an XS script (#5623, epic #5119): `host(g)` gives the `host` of `xs_run.Xs` for the side g (a
`gather.Gather`; the bots are `g.bots[i].g`, as in `scenario.attributes()`).

Minecraft feature: the scenario variables stay scores of `aoe_var` (the datapack triggers read them); the resources stay
in the stock of `Gather`. XS itself has no Minecraft feature (#5610). An unknown player or attribute gives one warning
line and 0, as an unknown name (`Xs.warn`), and the script goes on.
"""
import os
import re
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402

POPULATION = {11: (lambda x: x.units, lambda x: x.soldiers),           # cAttributePopulation
              37: (lambda x: x.units,),                                # cAttributeCivilianPopulation
              40: (lambda x: x.soldiers,)}                             # cAttributeMilitaryPopulation


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
    data = getattr(g, "data", None) or {}
    seed = zlib.crc32(f"{data.get('map_size')}-{len(data.get('objects', ()))}".encode())   # the map, not the clock
    rng, context = np.random.default_rng(seed), [g.player]

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
        return context[0] if int(player) == -1 else int(player)

    def player_data(player):
        return data.get("players", {}).get(str(who(player)))

    def map_name(extension=False):
        lobby = data.get("lobby", {})
        name = lobby.get("scenario") or lobby.get("script") or ""
        return name if extension else os.path.splitext(name)[0]

    def in_game(player):
        x = side(player)
        return bool(x) and not getattr(x, "lost", False)

    return {"xsGetContextPlayer": lambda: context[0],
            "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetHandicapMultiplier": lambda player=-1: 1.0,           # the game program has no handicap
            "xsGetMapHeight": size,
            "xsGetMapName": map_name,
            "xsGetMapSeed": lambda: int(seed & 0x7FFFFFFF),
            "xsGetMapTileAttribute": tile,
            "xsGetMapWidth": size,
            "xsGetNumPlayers": lambda: len(data.get("players", {})) + 1,   # with gaia, as AoE2
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerInGame": in_game,
            "xsGetPlayerName": lambda player=-1: (player_data(player) or {}).get("name", f"Player {who(player)}"),
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetRandomNumber": lambda: int(rng.integers(0, 32768)),
            "xsGetRandomNumberLH": lambda low, high: int(rng.integers(int(low), max(int(high), int(low) + 1))),
            "xsGetRandomNumberMax": lambda m: int(rng.integers(0, max(int(m), 1))),
            "xsGetTurn": lambda: int(recap.game_time(g) * 20),          # one turn per Minecraft tick (a choice)
            "xsGetWorldPlayerId": who,
            "xsGetWorldTime": lambda: int(recap.game_time(g) * 1000),   # milliseconds
            "xsPlayerAttribute": attribute,
            "xsSetContextPlayer": lambda player: context.__setitem__(0, int(player)),
            "xsSetPlayerAttribute": set_attribute,
            "xsSetTriggerVariable": set_variable,
            "xsTriggerVariable": variable}
