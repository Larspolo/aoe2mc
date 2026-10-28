"""
The fog of war for the units in the game program (#1389, epic #1387). The player does not see the enemy units out of
the line of sight of the own and allied units, buildings and construction sites (Gather.seen_tiles, #1388). An enemy
unit shows again when it comes into sight, as in AoE2 with the game setting "Reveal map: normal" (the default).
`game/run.py --reveal all` turns it off (AoE2 "All visible"). The cheat code "polo" turns it off and on (toggle, #1390).
The castle technology Spies turns it off for ever (reveal, #2193). The Mapuche see the enemy castles, the Vietnamese
the enemy start town centers at the start (revealed, civs.REVEAL, #2311). The setting "Shared Exploration" off
(`--shared-exploration off`, #2602) takes the sight of the allies away: each player sees only through the own ones.

Minecraft feature: Paper Player#hideEntity through the plugin (`aoe hide`, `aoe show`, as Replay.fog, #1302). It hides
the units only for the players on the team of the player (`team=p1`), not for a spectator. The plugin hides them also
for a player who joins later. Only the changes go out: at most one hide and one show command per update (RCON_MAX).

The minimap (#2583, epic #2580): each update also sends the sight of the player to the fog of its team on map 0
(Minimap.java: `aoe minimap fog T N pN`, `see pN`, `dim pN`, minimap()): unexplored tiles are black, explored tiles out
of sight dark, and an enemy building shows on the minimap of a team only after a tile of it was in its sight. A saved
game keeps the explored tiles (savegame.explored, #2677): after a load the first update sends them all again.
The team spec of the spectators (#2898) gets no hide and no minimap fog: Minimap.java draws the whole map for a player
with no team fog (#2899). The game mode spectator shows no held item, so a spectator sees map 0 only in a follow view.

    fog.tick(g)    # gather.Gather.run: once each EVERY seconds, on Paper only; run.Side.step for player 2 (#1631)
"""
EVERY = 1.0             # real seconds between two updates (Replay.fog: one each second of the replay)


def gathers(g):
    """The Gather g and the other Gathers of the game: its bots and, in a game of two people, the Gathers of the other
    persons (g.peers, run.play, #1631), each one time."""
    out = [g]
    for h in [*(b.g for b in g.bots), *g.peers]:
        if all(h is not o for o in out):
            out.append(h)
    return out


def shares(g, h):
    """True when Gather h sees for the player of g: the same player, or an ally with "Shared Exploration" on (#2602)."""
    import gather                                                  # gather imports fog
    return h.player == g.player or g.data.get("shared_exploration", True) and gather.allied(g.players, g.player, h.player)


def units(g):
    """({uuid: name} of the units that see for the player: its own and those of its allied bots (shares), {uuid: name}
    of the enemy units: of aoe2mc.json and of the enemy bots). An ally that does not share is in neither."""
    import gather                                                  # gather imports fog
    own, foe = {}, dict(g.enemies)
    for h in gathers(g):
        mine = dict.fromkeys(h.villagers, "VILLAGER") | h.soldiers
        if shares(g, h) or not gather.allied(g.players, g.player, h.player):
            (own if shares(g, h) else foe).update(mine)
    return own, {u: n for u, n in foe.items() if u not in own}     # a converted unit is own (monk.py)


def seen(g):
    """The UUIDs of the units of the players that "Set Player Visibility" shows to the player of g (scenario.visibility,
    #2774): update does not hide them out of sight."""
    sees = set(g.players.get(str(g.player), {}).get("sees", []))
    if not sees:
        return set()
    out = {o["uuid"] for o in g.data["objects"] if o["kind"] == "unit" and o["player"] in sees and o.get("uuid")}
    for h in gathers(g):
        if h.player in sees:
            out |= set(h.villagers) | set(h.soldiers)
    return out


def targets(g):
    """The target UUIDs of the own and allied buildings and construction sites (combat.target_uuid): Gather.where
    answers the live ones in the same commands as the units, so a destroyed building costs no command (#1470)."""
    import combat
    return {combat.target_uuid(fp) for h in gathers(g) if shares(g, h)
            for fp in [o["footprint"] for o in h.data["objects"]
                       if o["kind"] == "building" and o["player"] == h.player and "footprint" in o]
            + [[s["footprint"][i] for i in (0, 2, 1, 3)] for s in h.sites]}


def update(g, pos):
    """The hide and show commands for the feet positions pos {uuid: (x, y, z)} of the units and the building targets
    (targets); a dead unit is not in pos, so it gives no command, and a destroyed building gives no sight. A unit inside a siege tower stays as siege_tower.py hid it."""
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    own, foe = units(g)
    tiles = set().union(*(h.seen_tiles(pos, pos.keys()) for h in gathers(g) if shares(g, h)))   # a destroyed building sees nothing
    tiles |= revealed(g, start=not state.setdefault("started", False))
    state["started"] = True
    state["tiles"] = tiles                                             # the sight for the minimap (#2583)
    towers = set().union(*vars(g).get("towers", {}).values())
    shown = seen(g)
    out = {u for u, p in pos.items() if u in foe and u not in towers and u not in shown
           and (int(p[0] // g.map.T), int(p[2] // g.map.T)) not in tiles}
    hidden = state["hidden"]
    hide, show = sorted(out - hidden), sorted((hidden & pos.keys()) - out - towers)
    state["hidden"] = out | (hidden & towers)
    return commands(g, "hide", hide) + commands(g, "show", show)


def revealed(g, start=False):
    """The tiles of the enemy buildings that the civilization of the player sees at any distance (civs.REVEAL, #2311):
    the Mapuche see the enemy castles, the Vietnamese the enemy town centers of aoe2mc.json at the start (start: the
    first update) of the game. The game program has no explored tiles, so a revealed building gives sight on its tiles."""
    import civs, gather
    kinds = civs.REVEAL.get(civs.civ(g), ())
    if not kinds:
        return set()
    T, out = g.map.T, set()
    for name, first in kinds:
        rects = [[o["footprint"][i] for i in (0, 2, 1, 3)] + [o["player"]] for o in g.data["objects"]
                 if o["kind"] == "building" and o["name"] == name and "footprint" in o]
        rects += [[*s["footprint"], h.player] for h in gathers(g) for s in h.sites
                  if s["name"] == name and s["progress"] >= 1] * (not first)   # a castle of the game: complete
        for x0, x1, z0, z1, p in rects * (start or not first):
            if p and not gather.allied(g.players, g.player, p):
                out |= {(x, z) for x in range(int(x0 // T), int((x1 - 1) // T) + 1)
                        for z in range(int(z0 // T), int((z1 - 1) // T) + 1)}
    return out


def commands(g, verb, uuids):
    """The plugin commands "aoe hide" or "aoe show" of the sorted uuids for the team of the player, below RCON_MAX."""
    import replay
    who, k = f"@a[team=p{g.player}]", (replay.RCON_MAX - 40) // 37   # UUIDs per command (36 characters and a space)
    return [f"aoe {verb} {who} {' '.join(uuids[i:i + k])}" for i in range(0, len(uuids), k)]


def toggle(g):
    """The cheat code "polo" (#1390): no fog (g.reveal "all") shows all hidden enemy units at once, except the units
    inside a siege tower; a second "polo" puts the fog back at the next tick. Returns the new g.reveal."""
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    if g.reveal == "all":
        g.reveal, state["at"] = "normal", None
        return g.reveal
    g.reveal = "all"
    reveal(g)
    return g.reveal


def reveal(g):
    """Show all hidden enemy units at once, except the units inside a siege tower: "polo" and Spies (#2193)."""
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    towers = set().union(*vars(g).get("towers", {}).values())
    for c in commands(g, "show", sorted(state["hidden"] - towers)):
        g.command(c)
    state["hidden"] &= towers
    if state.pop("map", None) is not None:                             # the whole minimap shows (#2583)
        g.command(f"aoe minimap fog off p{g.player}")


def tick(g):
    """Update the fog each EVERY seconds: hide the enemy units that left the sight, show the ones that came in."""
    if not g.paper or g.reveal == "all" or "SPIES" in getattr(g, "techs", ()):   # Spies: the player sees what the
        return                                                     # enemies see, so all their units (#2193)
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    now = g.clock()
    if state["at"] is not None and now - state["at"] < EVERY:
        return
    state["at"] = now
    own, foe = units(g)
    for c in update(g, g.where(set(own) | set(foe) | targets(g))) + minimap(g, state):
        g.command(c)


def minimap(g, state):
    """The commands of the fog of the team of g on the minimap (#2583, Minimap.java): the fog starts all unexplored,
    then only the changes of the tiles in sight (state["tiles"] of update) and of the explored tiles out of sight, as
    the live replay does for its view player (Replay.minimap_fog)."""
    import replay
    T, team = g.map.T, f"p{g.player}"
    n = g.data.get("map_size") or len(getattr(g.map, "ground", ())) // T   # tiles of a map side
    if not n:
        return []
    inside = {(x, y) for x, y in state.get("tiles", ()) if 0 <= x < n and 0 <= y < n}
    explored = state.setdefault("explored", set())
    explored |= inside
    new = "map" not in state
    old_see, old_dim = state.get("map") or (set(), set())
    state["map"] = (inside, explored - inside)
    return [f"aoe minimap fog {T} {n} {team}"] * new + replay.runs(f"aoe minimap see {team}", inside - old_see) + \
        replay.runs(f"aoe minimap dim {team}", explored - inside - old_dim)
