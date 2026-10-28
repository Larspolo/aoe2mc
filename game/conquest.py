"""
The AoE2 conquest rule in the game program (#1135, epic #1134): a player without units and buildings is defeated, and
the last player wins. gather.Gather.run calls tick() each EVERY seconds (not each tick: one command per player and
check). The bot of player 2 has an own Gather that steps without run(), so only the game of the human player checks.
A unit is an entity with the tag aoe2mc.p<n> of its player (units.make_entity, also trained units), not its horse,
camel or boat (units.MOUNT). A building is the target entity of combat.building in the team p<n>: walls, gates and
Gaia objects have no target (combat.BUILDINGS), so they do not keep a player alive (AoE2 wiki, "Conquest"). A
construction site of the player counts as a building, as a foundation in AoE2. A complete one of combat.BUILDINGS
counts by its target entity (build.target), as a building of the map: when it falls, it counts no more (#3008).
Only a player that had units or buildings once can lose: a player of the scenario with nothing (most test maps), or with
its entities not loaded yet, is not in the game. A defeated player loses its rest (cheats.destroy), the chat says so and
its people see "Defeat" (defeat(), also for Regicide, Sudden Death and the code "resign"). The others play on, also
after a defeat of player 1 (decision #3103, A): the game ends (g.ended) when only allies are left (finish()), or at once
when no person is left (only bots).
Allies (the `team` of aoe2mc.json, gather.allied, #1313) win together, as in AoE2: "Victory" when all players of the
other teams are defeated, also while an ally is still in the game. A defeated ally does not end the game.
The AoE2 setting "Last Man Standing" (g.victory "last-man-standing", #2358): when only allies are left, the alliances
end (no `team` in g.players, the plugin command `aoe allies`) and the chat says so; only the last player alive wins.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from units import MOUNT  # noqa: E402

import cheats  # noqa: E402

EVERY = 3.0          # seconds between two checks


def alive(g, n):
    """Player n has a unit, a building or a construction site that counts in the AoE2 conquest."""
    import combat                                                   # combat imports gather, which imports this module
    return any(s["player"] == n and not (s.get("done") and (s["name"] in combat.BUILDINGS or s["name"] in combat.WALLS)
                                         and not s.get("lasting")) for s in g.sites) or any(
        "passed" in g.command(f"execute if entity {sel}")
        for sel in (f"@e[tag=aoe2mc.p{n},tag=!{MOUNT}]", f"@e[tag=aoe2mc.building,team=p{n},tag=!aoe2mc.wall]"))


def scored(g, n):
    """The scenario mode: the score #p<n> of aoe_lost, for the trigger condition "Player Defeated" (#2710)."""
    from gather import has_mode                                     # gather imports this module
    if has_mode(g, "scenario"):
        g.command(f"scoreboard players set #p{n} aoe_lost 1")


def main(g):
    """The Gather of player 1 from any Gather of the game: a person knows it (peers), a bot (share). Its run() checks the
    ends, and its `defeated` set holds the players that are out."""
    return g.peers[0] if g.peers else getattr(g, "share", None) or g


def left(g):
    """The players that are still in the game: the ones that had units or buildings once, and the players of the people
    and the bots, less the defeated ones."""
    from fog import gathers                                         # fog imports gather, which imports this module
    lost = vars(g).setdefault("defeated", set())
    return (vars(g).get("conquest_seen", set()) | {h.player for h in gathers(g)}) - lost - {0}


def defeat(g, n, text=None):
    """Player n is out of the game: defeated or resigned (decision #3103, A, as AoE2). Its rest goes, the chat says so
    and its people see "Defeat"; the others play on until finish() ends the game. When no person is left (only bots),
    the game ends at once, with no destroy (a one-person game ends as before, #1936)."""
    from fog import gathers
    from gather import allied                                       # gather imports this module
    g = main(g)
    vars(g).setdefault("defeated", set()).add(n)
    vars(g).setdefault("conquest_seen", set()).add(n)
    scored(g, n)
    rest = left(g)
    if not any(h.player in rest for h in gathers(g) if not getattr(h, "share", None)):
        return cheats.over(g, lambda p: bool(rest) and all(allied(g.players, p, k) for k in rest))
    cheats.destroy(g, n)
    g.command("tellraw @a " + json.dumps({"text": text or f"Player {n} is defeated.", "color": "red"}))
    cheats.title(g, n, "Defeat", "red")
    finish(g)


def finish(g):
    """End the game when a rival lost and only allies are left: the team wins together, also a player of it that lost
    before (#1313, decision #3103). Last Man Standing: last_man() ends it."""
    from gather import allied                                       # gather imports this module
    rest, lost = left(g), vars(g).get("defeated", set())
    if g.ended or not rest or g.victory == "last-man-standing":
        return
    one = min(rest)
    if any(not allied(g.players, one, n) for n in lost) and all(allied(g.players, a, b) for a in rest for b in rest):
        cheats.over(g, lambda p: allied(g.players, p, one))


def tick(g):
    """Check the players each EVERY seconds: defeat the ones without units and buildings, end the game."""
    if g.ended or g.victory == "custom" or g.clock() < vars(g).get("conquest_at", 0.0):   # a scenario: triggers (#2567)
        return
    g.conquest_at = g.clock() + EVERY
    seen, lost = vars(g).setdefault("conquest_seen", set()), vars(g).setdefault("defeated", set())
    for n in sorted(int(p) for p in g.players if int(p) and int(p) not in lost):
        if alive(g, n):
            seen.add(n)
        elif n in seen:
            defeat(g, n)
            if g.ended:
                return
    from gather import allied, allies_command                       # gather imports this module
    if g.victory == "last-man-standing":
        return last_man(g, seen - lost, lost, allied, allies_command)
    finish(g)


def last_man(g, left, lost, allied, allies_command):
    """Last Man Standing (#2358): the last player alive wins alone; when a rival lost and only allies are left, they
    become enemies (the Minecraft teams of the plugin, `aoe allies`)."""
    if not lost:
        return
    if len(left) == 1:
        winner, = left
        return cheats.over(g, lambda n: n == winner)
    if len(left) > 1 and all(allied(g.players, a, b) for a in left for b in left):
        for n in left:
            g.players[str(n)].pop("team", None)
        import owners                                                  # owners -> build -> gather -> cheats
        owners.update_enemies(g)                                       # the last allies are enemies (#2996)
        if g.paper:
            g.command(allies_command(g.players))
        g.command("tellraw @a " + json.dumps({"text": "Only allies are left: the alliances end. The last player alive "
                                                      "wins.", "color": "gold"}))
