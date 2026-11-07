"""The map editor mode of the game program (#5999, epic #5998).

    python3 game/run.py WORLD --editor OUT.aoe2scenario

The world starts with no game time: no play(), so no gather tick, no bot, no age, no victory and no fog. The units
and buildings stand still. The person paints the terrain with the creative inventory (run.py sets creative mode) and
places water. The chat word `save` and the stop of the server write a save folder (savegame.write, no game state)
and export it to OUT (export.export): export.ground() gives each painted tile the AoE2 terrain of its new top block.
Vanilla logs each chat line ("<name> text"), so the log of the server is enough: no plugin command.
The chat word `palette` opens the palette of objects (#6013): tabs Units, Buildings, Resources and Gaia (#6036); a right click on an
object places it where the person looks (place), and the save keeps it.
The chat word `remove` removes the object that the person looks at (#6002): its entities, the blocks of a building
or resource down to the ground of its tiles, and its entry of the save (State.removed: start objects; State.placed).
The chat word `players` opens the players menu (#6003): the current player of the palette, and the civilization, the
start resources and the starting age of each player. They go into the players of aoe2mc.json (State.data), and save
writes that file into the save folder: export.export reads them there, with no new code path.
The players menu also sets the team of the current player and the victory setting (#6032). The chat word `messages`
gives the person a book and quill for each chapter of the scenario texts (a vanilla item); save reads the pages of
the books back into "messages" of aoe2mc.json.
The chat word `options` opens the options menu (#6085): it disables technologies, buildings and units of the current
player ("disabled" of its entry in aoe2mc.json, as read_scenario writes it).
"""
import functools
import json
import os
import re
import time

import export
import gather
import lang
import menu
import numpy as np
import savegame
import table

REMOVE = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> remove\s*$")    # the chat word of remove (#6002)
PALETTE = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> palette(?:\s+(.*?))?\s*$")   # the chat word of the palette (#6013); a word searches (#6058)
MESSAGES = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> messages\s*$")   # the books of the texts (#6032)
OPTIONS = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> options\s*$")   # the options menu (#6085)
PLAYERS = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> players\s*$")   # the players menu (#6003)
CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> save\s*$")   # the chat word, as the server logs it


class State:
    """The light state of the editor (#6012): no Gather, but what menu, build.free and build.found need: the map of
    aoe2mc.json, the open chest menus, command, and the list of placed objects (AoE2 unit ID, owner, tile)."""

    def __init__(self, game, data=None):
        if data is None:
            with open(os.path.join(game.world, "aoe2mc.json")) as f:
                data = json.load(f)
        self.game, self.data, self.map = game, data, gather.Map(data)
        self.menus, self.placed, self.person, self.picked = {}, [], None, {}   # picked: player -> object name
        self.removed = set()                                           # the indices of removed start objects (#6002)
        self.writers = set()                                          # the persons with the books (#6032)
        self.player = PLAYER                                          # the owner of the next object (#6003)

    def command(self, cmd):
        return self.game.command(cmd)

    pos, look = gather.Gather.pos, gather.Gather.look                  # the eye of the person (data get entity)

    def place(self, unit_id, player, tile):
        """Add an object to the save: tile (x, y) in the tiles of the world."""
        self.placed.append({"id": int(unit_id), "player": int(player), "tile": [float(v) for v in tile]})

    def dump(self):
        return {"placed": list(self.placed), "removed": sorted(self.removed)}


HIGH = 40                                                              # blocks over the ground that remove clears
PAGE = 45                                                              # items per page; the last row: the tabs
TAB_ICONS = ("armor_stand", "bricks", "gold_ore", "tuff", "golden_helmet", "flower_pot")      # Units, Buildings, Resources, Cliffs, Heroes, Gaia
GAIA_MARKS = tuple(r["name"] for r in table.load("editor_gaia.jsonl"))   # name parts that place_objects draws (#6036)
PLAYER = 1                                                             # the first current player


def new_world(world, size, terrain="GRASS_1", players=2):
    """A new empty map (#6077): all tiles of the terrain (default GRASS_1), players human players (1 to 8), converted
    into world. An unknown terrain or a player count out of range raises ValueError (#6078)."""
    import difflib

    import scenarios
    from AoE2ScenarioParser.datasets.terrains import TerrainId

    import aoe2mc
    if terrain not in TerrainId.__members__:
        close = ", ".join(difflib.get_close_matches(terrain, TerrainId.__members__, n=3))
        raise ValueError(f"unknown terrain {terrain!r}" + (f": did you mean {close}?" if close else ""))
    if not 1 <= players <= 8:
        raise ValueError(f"--players {players}: give 1 to 8 players")
    scn = scenarios.new_scenario(size)
    scn.player_manager.active_players = players
    for t in scn.map_manager.terrain:
        t.terrain_id = TerrainId[terrain].value
    src = scenarios.save(scn, os.path.abspath(world).rstrip(os.sep) + ".new.aoe2scenario")
    aoe2mc.convert(src, world)
    return world


@functools.lru_cache(maxsize=None)                                   # the data does not change while the editor runs (#6056)
def tabs():
    """The palette tabs (#6013): [(tab, [object names])], from the data files: the units of train, the buildings of
    the build menu, the mines, fish and hunts of gather, the forest trees and the bushes of
    rmap (#6016); at the end of the units the other units of AoE2ScenarioParser (the king, Gaia, ships), and the heroes
    (#6035). Only names with an AoE2 unit ID (export.unit_id) that units.py can show (units.classify)."""
    import build
    import train
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import rmap
    import units
    known = lambda names: [n for n in dict.fromkeys(names) if export.unit_id(n) is not None]   # noqa: E731
    shown = lambda names, hero=False: [n for n in known(names) if units.classify(n, hero)]   # noqa: E731
    return [("units", known([r["name"] for r in train.UNIT_ROWS] + shown(e.name for e in UnitInfo))),
            ("buildings", known(build.MENU)),
            ("resources", known([t["name"] for t in gather.ROWS if {"mine", "fish", "hunt"} & set(t)] +
                                 sorted(set(rmap.FOREST_TREES.values())) +
                                 [n for n in sorted(rmap.OBJECTS) if "BUSH" in n])),
            ("cliffs", cliffs()), ("heroes", shown((e.name for e in HeroInfo), True)), ("gaia", known(gaia_names()))]


def cliffs():
    """The cliff objects of AoE2 (#6037): the CLIFF_ names of OtherInfo. The converter draws them as rock ridges
    (aoe2mc.cliff_ridges, with the rocks of their terrain), and replay.draw of kind "O" uses that code."""
    from AoE2ScenarioParser.datasets.other import OtherInfo
    return [n for n in OtherInfo.__members__ if n.startswith("CLIFF")]


def gaia_names():
    """The other objects (OtherInfo) that the converter draws (#6036): relics, rocks, ruins, mountains, monuments and
    decor, as the rules of aoe2mc.place_objects. Not the cliffs (the tab Cliffs, #6037), the trees, mines and bushes
    of the Resources tab, the flags (of a player) and the objects with no blocks."""
    import aoe2mc
    names = sorted({v[1] for v in aoe2mc.object_kinds(old=False).values() if v[0][:1] == "O"})
    shown = tuple(k for k, r in aoe2mc.OBJECT.items() if not {"mob", "no_blocks", "rocks"} & set(r))
    return [n for n in names if kind(n) == "O" and not n.startswith(("CLIFF", "UNKNOWN")) and not any(k in n for k in ("BUSH", "FLAG",
            "MINE", "TREE")) and (any(k in n for k in GAIA_MARKS) or n.startswith(shown + aoe2mc.MOUNTAINS))]


VEHICLES = ("armor_stand", "boat", "minecart", "raft")                # entities with an item of the same name
NO_ITEM = ("air", "barrier", "fire", "lava", "light", "water")         # blocks with no item: not an icon
ITEM_OF = {"sweet_berry_bush": "sweet_berries"}                       # a block whose item has another name


def icon(name, hero=False, unit=None):
    """The item that shows palette object name (#6057), or None: a unit, a hero or an animal: the spawn egg of its mob
    (of its rider on a mount), a boat, a minecart or an armor stand: its own item; another object: the most common
    block that the converter draws for it (aoe2mc.place_objects). unit: kind(name) == "U", if known (it is slow)."""
    import aoe2mc
    import units
    if mob := aoe2mc.object_mob(name):
        return f"{mob}_spawn_egg"
    if kind(name) == "U" if unit is None else unit:
        e = units.make_entity(dict(name=name, player=PLAYER, rotation=0.0, hero=hero), {}, (0.0, 0.0, 0.0),
                              np.random.default_rng(1))
        if e is None:
            return None
        kind_id = str(e["id"]).removeprefix("minecraft:")
        if kind_id.endswith(VEHICLES):
            return kind_id
        rider = next(iter(e.get("Passengers", ())), None)
        if rider is not None and "item" in rider:                     # a display (a war wagon): its item
            return str(rider["item"]["id"]).removeprefix("minecraft:")
        return f"{str(rider['id']).removeprefix('minecraft:') if rider is not None else kind_id}_spawn_egg"
    T = 4
    cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32), {0: "GRASS_1"}, T, 1,
                          np.random.default_rng(1))
    E, _ = aoe2mc.place_objects([dict(kind="O", name=name, player=0, x=2.0, y=2.0, rotation=0.0, hero=False,
                                      garrisoned=False)], {}, cols, np.random.default_rng(1))
    ids = np.concatenate([p[3] for p in E.parts] or [np.zeros(0, np.uint16)])
    blocks = [aoe2mc.B.states[i].removeprefix("minecraft:").partition("[")[0] for i in np.unique(ids)]
    counts = {b: 0 for b in blocks}
    for i, n in zip(*np.unique(ids, return_counts=True)):
        counts[aoe2mc.B.states[i].removeprefix("minecraft:").partition("[")[0]] += int(n)
    counts = {b.replace("wall_", ""): n for b, n in counts.items() if not b.endswith(NO_ITEM)}
    return ITEM_OF.get(b := max(counts, key=counts.get), b) if counts else None


_ICONS = {}


def icons():
    """{name: item} of all palette objects with an icon, computed one time (#6057)."""
    import aoe2mc
    if not _ICONS:
        kinds = aoe2mc.object_kinds(old=False)                         # kind() of each name, one time
        for t, names in tabs():
            for n in names:
                unit = kinds.get(export.unit_id(n), ("U",))[0][:1] in "UH"
                if t != "buildings" and (i := icon(n, t == "heroes", unit)):
                    _ICONS[n] = i
    return _ICONS


def open_menu(g, player, tab=0, page=0, word=None):
    """Show tab of the palette at page. A click on a tab opens it; a click on an object picks it (the next right click
    places it), a right click on an object places it at once where the person looks. A word (#6058): the objects of
    all tabs whose shown name has it, as the search box of the AoE2 editor; no match: a chat text and no menu."""
    import build
    all_tabs = tabs()
    names = all_tabs[tab][1]
    icon = {}
    if word:
        found = [(n, TAB_ICONS[k]) for k, (_, ns) in enumerate(all_tabs) for n in ns if word.lower() in build.pretty(n).lower()]
        icon = dict(reversed(found))                                    # the icon of the first tab of a name
        names = list(dict.fromkeys(n for n, _ in found))
        if not names:
            build.say(g, player, lang.text("aoe2mc.editor.no_match", word))
            return None
    shown = names[page * PAGE:(page + 1) * PAGE]
    pages = max(1, -(-len(names) // PAGE))

    def click(p, slot, shift, right=False):
        if slot >= PAGE + len(all_tabs) and slot - PAGE - len(all_tabs) < 2:   # the page buttons
            open_menu(g, p, tab, (page + (1 if slot == PAGE + len(all_tabs) + 1 else -1)) % pages, word)
        elif slot >= PAGE:
            if slot - PAGE < len(all_tabs):
                open_menu(g, p, slot - PAGE)
        elif slot < len(shown):
            g.picked[p] = shown[slot]
            if right and (view := g.look(p)):
                place(g, p, shown[slot], *view)
    items = [(i, build.ICONS.get(n) or icons().get(n) or icon.get(n, TAB_ICONS[tab]), build.pretty(n), "")
             for i, n in enumerate(shown)]
    items += [(PAGE + k, TAB_ICONS[k], t.title(), "")
              for k, (t, _) in enumerate(all_tabs)]
    if pages > 1:
        items += [(PAGE + len(all_tabs), "arrow", "<", f"{page + 1}/{pages}"),
                  (PAGE + len(all_tabs) + 1, "spectral_arrow", ">", f"{page + 1}/{pages}")]
    return menu.show(g, player, "Palette", items, click)


def kind(name):
    """"B" (a building), "U" (a unit or an animal: an entity) or "O" (another object: its blocks), as the converter
    (aoe2mc.object_kinds)."""
    import aoe2mc
    return aoe2mc.object_kinds(old=False).get(export.unit_id(name), ("U",))[0][:1].replace("H", "U")   # a hero: an entity


def place(g, player, name, eye, d):
    """Place object name of PLAYER (an animal: of Gaia) at the ground that the person looks at: a building finished, a
    unit as an entity (units.make_entity), a resource with its blocks. Not on the footprint of another object
    (build.free). Returns the placed object (dict of State.placed) or None."""
    import build
    cell = g.map.pick_ground(eye, d)
    if cell is None:
        return None
    if name in build.WALLS:
        return wall(g, player, name, cell)
    return place_at(g, player, name, cell)


def wall(g, player, name, cell):
    """A wall line as the AoE2 editor (#6038): the first click keeps the start cell (the action bar says it); the
    second places a segment on each tile from the start to cell (aoe2mc.wall_tiles, as build.wall). Returns the
    first placed segment or None."""
    import build
    start = vars(g).setdefault("wall_start", {}).pop(player, None)
    if start is None or start[0] != name:
        g.wall_start[player] = (name, cell)
        g.command(f"title {player} actionbar " + json.dumps(lang.text("aoe2mc.build.wall_end", build.pretty(name),
                                                                       color="gray")))
        return None
    T = g.map.T
    done = [place_at(g, player, name, (x * T + T // 2, z * T + T // 2))
            for x, z in build.wall_tiles(start[1][0] // T, start[1][1] // T, cell[0] // T, cell[1] // T)]
    return next((o for o in done if o), None)


def place_at(g, player, name, cell):
    """Place object name at block cell (x, z) of the ground (place)."""
    import build
    import replay

    import units
    k, T = kind(name), g.map.T
    rect = build.area(g, name, cell) if k == "B" else (cell[0] // T * T, cell[0] // T * T + T, cell[1] // T * T,
                                                       cell[1] // T * T + T)
    if name.startswith("CLIFF"):                                       # 3 x 3 tiles, as the converter
        import aoe2mc
        c = (cell[0] // T + 0.5, cell[1] // T + 0.5)
        rect = aoe2mc.object_footprint(dict(name=name, x=c[0], y=c[1]), T)
    if not build.free(g, rect):
        build.say(g, player, lang.text("aoe2mc.build.space", build.pretty(name).lower()))
        return None
    x0, x1, z0, z1 = rect
    tile = ((x0 + x1) / 2 / T, (z0 + z1) / 2 / T)
    owner = 0 if name in (t := dict(tabs()))["resources"] + t["gaia"] or name.startswith("CLIFF") else vars(g).get("player", PLAYER)   # a resource, a relic or a cliff is of Gaia
    if k == "U":
        x, z = (x0 + x1) // 2, (z0 + z1) // 2
        pos = (x + 0.5, float(g.map.y(x, z)), z + 0.5)
        players = {int(p): v for p, v in g.data.get("players", {}).items()}
        hero = name in dict(tabs())["heroes"]
        nbt = units.make_entity(dict(name=name, player=owner, rotation=0.0, hero=hero), players, pos, np.random.default_rng())
        if nbt is None:
            return None
        kind_id = str(nbt.pop("id"))
        del nbt["Pos"]
        g.command(f"summon {kind_id} {pos[0]} {pos[1]} {pos[2]} {units.summon_snbt(nbt)}")
    else:
        r = replay.Replay(g, g.data)
        for c in r.building(name, owner, *tile, kind=k):
            g.command(c)
        g.map.blocked |= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    g.place(export.unit_id(name), owner, tile)
    g.placed[-1]["rect"] = list(rect)                                  # for remove; export reads only id, player, tile
    if k == "U":
        g.placed[-1]["unit"] = True
    return g.placed[-1]


def rect_of(g, o):
    """(the block footprint (x0, x1, z0, z1), True for an entity only) of start object o of aoe2mc.json."""
    T = g.map.T
    if o["kind"] == "building" and "footprint" in o:
        x0, z0, x1, z1 = o["footprint"]
        return (x0, x1, z0, z1), False
    tile = int(o["tile"][0]), int(o["tile"][1])
    if o["kind"] == "other" and tile in g.map.feet:                    # a mine or a tree: its footprint
        return tuple(g.map.feet[tile]), False
    return (tile[0] * T, tile[0] * T + T, tile[1] * T, tile[1] * T + T), o["kind"] == "unit"


def remove(g, player, eye, d):
    """Remove the object at the ground that the person looks at (#6002): a placed one first (the newest), else a start
    object. Its entities go, the blocks of a building or resource go down to the ground, and its cells are free for a
    new object. Returns the footprint (x0, x1, z0, z1) or None."""
    cell = g.map.pick_ground(eye, d)
    if cell is None:
        return None
    inside = lambda r: r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]   # noqa: E731
    hit = next(((i, tuple(o["rect"]), o.get("unit", False)) for i, o in reversed(list(enumerate(g.placed)))
                if "rect" in o and inside(o["rect"])), None)
    if hit:
        g.placed.pop(hit[0])
    else:
        hits = [(i, *rect_of(g, o)) for i, o in enumerate(g.data["objects"]) if i not in g.removed and "tile" in o]
        hit = next((h for h in hits if inside(h[1])), None)
        if hit is None:
            return None
        g.removed.add(hit[0])
    rect, unit = hit[1], hit[2]
    x0, x1, z0, z1 = rect
    g.command(f"kill @e[type=!player,x={x0},y=-64,z={z0},dx={x1 - x0 - 1},dy=400,dz={z1 - z0 - 1}]")
    if not unit:
        ys = [y for x in range(x0, x1) for z in range(z0, z1) if (y := g.map.y(x, z)) is not None]
        if ys:
            g.command(f"fill {x0} {min(ys)} {z0} {x1 - 1} {min(ys) + HIGH} {z1 - 1} air")
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        g.map.blocked -= cells
        for at in (g.map.farm_at, g.map.mine_at):
            for c in cells:
                at.pop(c, None)
    return rect


STEP = 100                                                             # a click on a resource: +100, shift: -100
CIV, RES, AGE, TEAM, WIN = 9, 18, 27, 36, 37                                              # the first slot of each row of the menu
RES_ICONS = ("bread", "oak_log", "gold_ingot", "cobblestone")


def info(g, p):
    """The entry of player p in the players of aoe2mc.json (a new player: a new entry)."""
    return g.data.setdefault("players", {}).setdefault(str(p), {})


def players_menu(g, player):
    """The players menu (#6003): row 1 the current player (Gaia, 1 to 8); a click on the civilization item: the next
    civilization (shift: the one before); row 3 the resources (click +STEP, shift -STEP); row 4 the age."""
    import civs
    names = [r["name"] for r in civs.ROWS]
    p = g.player
    me = info(g, p) if p else {}
    items = [(i, "player_head" if i == p else "skeleton_skull", "Gaia" if i == 0 else f"Player {i}", "current" if i == p else "")
             for i in range(9)]
    if p:
        age = me.get("age", "dark").lower().replace("-", "_")
        items += [(CIV, "white_banner", (me.get("civ") or "-").title(), "Click: next · Shift click: before")]
        items += [(RES + k, RES_ICONS[k], f"{r.title()}: {int(me.get('resources', {}).get(r, 0))}", f"Click: +{STEP} · Shift click: -{STEP}")
                  for k, r in enumerate(export.RESOURCES)]
        items += [(TEAM, "white_wool", f"Team: {me.get('team') or '-'}", "Click: next team (1 to 4, or none)")]
        items += [(AGE + k, "clock", a.name.replace("_", " ").title(), "current" if a.name == age.upper() + "_AGE" else "")
                  for k, a in enumerate(export.AGES)]
    win = (g.data.get("victory") or {}).get("condition", "standard")
    items += [(WIN, "gold_block", f"Victory: {win.replace('-', ' ').title()}", "Click: next condition")]

    def click(q, slot, shift, right=False):
        if slot < 9:
            g.player = slot
        elif p and slot == CIV:
            at = names.index(me["civ"]) if me.get("civ") in names else -1
            me["civ"] = names[(at + (-1 if shift else 1)) % len(names)]
        elif p and RES <= slot < RES + len(export.RESOURCES):
            res = me.setdefault("resources", {})
            r = export.RESOURCES[slot - RES]
            res[r] = max(0, int(res.get(r, 0)) + (-STEP if shift else STEP))
        elif p and AGE <= slot < AGE + len(export.AGES):
            me["age"] = export.AGES[slot - AGE].name[:-4].lower()
        elif p and slot == TEAM:
            me["team"] = (int(me.get("team") or 0) + 1) % (TEAMS + 1) or None
        elif slot == WIN:
            v = g.data.get("victory") or {}
            v["condition"] = victories()[(victories().index(win) + 1) % len(victories()) if win in victories() else 0]
            g.data["victory"] = v
        players_menu(g, q)
    return menu.show(g, player, "Players", items, click)


TEAMS = 4                                                              # the teams of the AoE2 lobby


def victories():
    """The conditions of run.VICTORIES that the scenario file has (VictoryCondition): the others are lobby settings."""
    import run
    from AoE2ScenarioParser.datasets.trigger_lists import VictoryCondition
    return [k for k in sorted(run.VICTORIES) if k.upper().replace("-", "_") in VictoryCondition.__members__]


def chapters():
    """The chapters of the scenario texts that the scenario file has (aoe2mc.CHAPTERS; objectives: no field)."""
    import aoe2mc
    return {k: v for k, v in aoe2mc.CHAPTERS.items() if k != "objectives"}


def books(g, player):
    """Give player a book and quill for each chapter (#6032), with the text of "messages" (pages of 1024 chars). A
    text longer than one RCON command (rcon.MAX) gets no book, so the save keeps it whole."""
    import rcon
    g.writers.add(player)
    texts = g.data.get("messages", {})
    for k, title in chapters().items():
        t = texts.get(k, "")
        pages = ",".join("{raw:%s}" % json.dumps(t[i:i + 1024]) for i in range(0, len(t), 1024))
        cmd = (f"give {player} minecraft:writable_book[custom_name={json.dumps(title)},"
               f"custom_data={{aoe_msg:\"{k}\"}},writable_book_content={{pages:[{pages}]}}]")
        if len(cmd.encode()) <= rcon.MAX:
            g.command(cmd)


TEXT = re.compile(r"""raw:\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')""")


def unquote(q):
    """The text of a quoted SNBT string."""
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), q[1:-1])


def read_books(g):
    """Read the pages of the books of the writers into "messages" (the pages of a chapter in order). A
    chapter with no book keeps its text."""
    texts = g.data.setdefault("messages", {})
    for player in sorted(g.writers):
        for k in chapters():
            out = g.command(f'data get entity {player} Inventory[{{components:{{"minecraft:custom_data":'
                            f'{{aoe_msg:"{k}"}}}}}}].components."minecraft:writable_book_content".pages') or ""
            if "has the following" in out:
                texts[k] = "".join(unquote(q) for q in TEXT.findall(out))


def save(game, out, state=None):
    """Write the world and the placed objects of state into a save folder and export it to out. Returns out."""
    game.command("save-off")
    game.command("save-all flush")
    if state and state.writers:
        read_books(state)
    try:
        folder = savegame.write(savegame.folder(game.world), game.world, state.dump() if state else None)
        if state:                                                      # the players of the menu (#6003)
            with open(os.path.join(folder, "world", "aoe2mc.json"), "w") as f:
                json.dump(state.data, f)
    finally:
        game.command("save-on")
    path = export.export(folder, out, heights=True)
    game.command("tellraw @a " + json.dumps(lang.text("aoe2mc.editor.saved", os.path.abspath(path), color="green")))
    return path


def words(game, seen):
    """(the new log length, the count of `save` chat lines in the log after seen)."""
    log = game.server.log
    return len(log), sum(1 for line in log[seen:] if CHAT.search(line))


def tick(state):
    """One click tick: the clicks of the open menus reach their handlers."""
    return menu.clicks(state) if state.menus else []


OPTION_TABS = ("technologies", "buildings", "units")                    # the tabs of the options menu (#6085)
OPTION_ICONS = ("enchanted_book", "bricks", "armor_stand")


def option_names(tab):
    """The names of options tab: the technologies that a player can research (train.TECHS), or the palette objects."""
    if OPTION_TABS[tab] == "technologies":
        import train
        return sorted(train.TECHS)
    return dict(tabs())[OPTION_TABS[tab]]


def options_menu(g, player, tab=0, page=0):
    """The options menu (#6085), as the Options tab of the AoE2 editor: a click disables an item of the current
    player, a second click enables it again ("disabled" of its entry in aoe2mc.json, sorted as read_scenario writes it)."""
    import build
    names = option_names(tab)
    pages = max(1, -(-len(names) // PAGE))
    shown = names[page * PAGE:(page + 1) * PAGE]
    me = info(g, g.player)
    word = lambda k: lang.text(f"aoe2mc.editor.options.{k}")["fallback"]   # noqa: E731  a menu takes plain text
    off = set(me.get("disabled", ()))

    def click(p, slot, shift, right=False):
        if slot < len(shown):
            off.symmetric_difference_update({shown[slot]})
            me["disabled"] = sorted(off)
            options_menu(g, p, tab, page)
        elif PAGE <= slot < PAGE + len(OPTION_TABS):
            options_menu(g, p, slot - PAGE)
        elif slot in (PAGE + len(OPTION_TABS), PAGE + len(OPTION_TABS) + 1):
            options_menu(g, p, tab, (page + (1 if slot == PAGE + len(OPTION_TABS) + 1 else -1)) % pages)
    items = [(i, "barrier" if n in off else build.ICONS.get(n) or icons().get(n) or OPTION_ICONS[tab], build.pretty(n),
              word("disabled" if n in off else "enabled"))
             for i, n in enumerate(shown)]
    items += [(PAGE + k, OPTION_ICONS[k], word(t), "") for k, t in enumerate(OPTION_TABS)]
    if pages > 1:
        items += [(PAGE + len(OPTION_TABS), "arrow", "<", f"{page + 1}/{pages}"),
                  (PAGE + len(OPTION_TABS) + 1, "spectral_arrow", ">", f"{page + 1}/{pages}")]
    return menu.show(g, player, word("title"), items, click)


def run(game, out, alive, state=None):
    """Answer the chat word `save` and the menu clicks while alive() (the console thread of run.main is alive)."""
    state = state or State(game)
    game.editor = state                                                # the save at the stop of run.main
    seen = len(game.server.log)
    game.command("tellraw @a " + json.dumps(lang.text("aoe2mc.editor.start", color="yellow")))   # the chat words, once
    while alive():
        tick(state)
        for line in game.server.log[seen:]:
            if m := PALETTE.search(line):
                open_menu(state, m.group(1), word=m.group(2))
            if (m := REMOVE.search(line)) and (view := state.look(m.group(1))):
                remove(state, m.group(1), *view)
            if m := MESSAGES.search(line):
                books(state, m.group(1))
            if m := PLAYERS.search(line):
                players_menu(state, m.group(1))
            if m := OPTIONS.search(line):
                options_menu(state, m.group(1))
        seen, n = words(game, seen)
        if n:
            print(f"Saved the map: {save(game, out, state)}")
        time.sleep(0.5)
