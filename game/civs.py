"""
The civilization bonuses of the players in the game program (#1089, part of #1088). WORK holds the work-rate bonuses of
the AoE2 DE civilizations (the AoE2 wiki, "Civilization bonuses" of each civilization): Gather.work_time divides the
time of one unit of resource by the factor of the player's civilization. The keys are the gather kinds of Gather:
"wood", "food" (forage bushes), "farm", "gold", "stone", "hunt" (hunted animals) and "sheep" (herdable animals).
Bonuses that the game program cannot use yet: Japanese fishing ships, Malian oyster gatherers, Spanish builders, the
Roman builders and repairers, the Georgian fortified church (+10 % near it), the Persian town centers and docks.
"""

# Work-rate factor of each civilization and gather kind (AoE2 DE, the AoE2 wiki). A missing kind is 1.
ROMAN = 1.05                                                       # Romans: villagers gather 5 % faster
WORK = {"BRITONS": {"sheep": 1.25},                                # shepherds work 25 % faster
        "CELTS": {"wood": 1.15},                                   # lumberjacks work 15 % faster
        "FRANKS": {"food": 1.15},                                  # foragers work 15 % faster
        "KHMER": {"farm": 0.95},                                   # farmers work 5 % slower (no drop-off)
        "KOREANS": {"stone": 1.2},                                 # stone miners work 20 % faster
        "MALIANS": {"gold": 1.1},                                  # gold miners work 10 % faster
        "MONGOLS": {"hunt": 1.4},                                  # hunters work 40 % faster
        "ROMANS": dict.fromkeys(("farm", "food", "gold", "hunt", "sheep", "stone", "wood"), ROMAN),
        "SLAVS": {"farm": 1.15},                                   # farmers work 15 % faster
        "TURKS": {"gold": 1.25}}                                   # gold miners work 25 % faster


def civ(g):
    """The civilization of the player of g (aoe2mc.json "players"), for example "CELTS", else None."""
    return g.data.get("players", {}).get(str(g.player), {}).get("civ")


def work(g, kind):
    """The work-rate factor of the civilization of the player of g for gather kind (WORK), else 1."""
    return WORK.get(civ(g), {}).get(kind, 1)
