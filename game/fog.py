"""
The fog of war for the units in the game program (#1389, epic #1387). The player does not see the enemy units out of
the line of sight of the own and allied units, buildings and construction sites (Gather.seen_tiles, #1388). An enemy
unit shows again when it comes into sight, as in AoE2 with the game setting "Reveal map: normal" (the default).
`game/run.py --reveal all` turns it off (AoE2 "All visible"). The cheat code "polo" turns it off and on (toggle, #1390).

Minecraft feature: Paper Player#hideEntity through the plugin (`aoe hide`, `aoe show`, as Replay.fog, #1302). It hides
the units only for the players on the team of the player (`team=p1`), not for a spectator. The plugin hides them also
for a player who joins later. Only the changes go out: at most one hide and one show command per update (RCON_MAX).

    fog.tick(g)    # gather.Gather.run: once each EVERY seconds, on Paper only
"""
EVERY = 1.0             # real seconds between two updates (Replay.fog: one each second of the replay)


def units(g):
    """({uuid: name} of the units that see for the player: its own and those of its allied bots, {uuid: name} of the
    enemy units: of aoe2mc.json and of the enemy bots)."""
    import gather                                                  # gather imports fog
    own, foe = {}, dict(g.enemies)
    for h in [g, *(b.g for b in g.bots)]:
        mine = dict.fromkeys(h.villagers, "VILLAGER") | h.soldiers
        (own if gather.allied(g.players, g.player, h.player) else foe).update(mine)
    return own, {u: n for u, n in foe.items() if u not in own}     # a converted unit is own (monk.py)


def update(g, pos):
    """The hide and show commands for the feet positions pos {uuid: (x, y, z)} of the units; a dead unit is not in
    pos, so it gives no command. A unit inside a siege tower stays as siege_tower.py hid it."""
    import gather
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    own, foe = units(g)
    tiles = set().union(*(h.seen_tiles(pos) for h in [g, *(b.g for b in g.bots)]
                          if gather.allied(g.players, g.player, h.player)))
    towers = set().union(*vars(g).get("towers", {}).values())
    out = {u for u, p in pos.items() if u in foe and u not in towers
           and (int(p[0] // g.map.T), int(p[2] // g.map.T)) not in tiles}
    hidden = state["hidden"]
    hide, show = sorted(out - hidden), sorted((hidden & pos.keys()) - out - towers)
    state["hidden"] = out | (hidden & towers)
    return commands(g, "hide", hide) + commands(g, "show", show)


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
    towers = set().union(*vars(g).get("towers", {}).values())
    for c in commands(g, "show", sorted(state["hidden"] - towers)):
        g.command(c)
    state["hidden"] &= towers
    return g.reveal


def tick(g):
    """Update the fog each EVERY seconds: hide the enemy units that left the sight, show the ones that came in."""
    if not g.paper or g.reveal == "all":
        return
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    now = g.clock()
    if state["at"] is not None and now - state["at"] < EVERY:
        return
    state["at"] = now
    own, foe = units(g)
    for c in update(g, g.where(set(own) | set(foe))):
        g.command(c)
