"""A villager with no task is a nitwit (#2761): a nitwit never takes a job site, so the vanilla YieldJobSite does no
path search to each villager near it (65 % of the server tick of the live replay of de-63.0 after 20 minutes)."""
import os
import shutil
import sys
import time

import pytest

import units

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402


def test_a_villager_with_no_task_is_a_nitwit():
    assert units.classify("VILLAGER_MALE", False)["VillagerData"]["profession"] == "minecraft:nitwit"
    assert units.classify("VILLAGER_FEMALE_LUMBERJACK", False)["VillagerData"]["profession"] == "minecraft:fletcher"
    assert replay.start_job("VILLAGER_FEMALE") == units.IDLE_JOB == "nitwit"


@pytest.mark.mc
def test_a_nitwit_takes_no_job_site_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not available")
    import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        for c in ("forceload add 0 0", "fill 0 99 0 12 99 12 stone", "fill 0 100 0 12 103 12 air",
                  "setblock 6 100 6 minecraft:composter"):               # a job site of a farmer
            game.command(c)
        for job in ("none", "nitwit"):                                 # with AI: as a walking unit of the replay
            game.command(f'summon villager 9.5 100 6.5 {{Tags:["j{job}"],Offers:{{Recipes:[]}},Xp:1,'
                         f'VillagerData:{{profession:"minecraft:{job}",level:2,type:"minecraft:plains"}}}}')

        def brain(job):
            return game.command(f"data get entity @e[tag=j{job},limit=1] Brain.memories") + \
                game.command(f"data get entity @e[tag=j{job},limit=1] VillagerData.profession")
        end = time.time() + 60
        while "job_site" not in brain("none"):                         # it takes the composter and is a farmer
            assert time.time() < end, f"the control villager took no job site in 60 s: {brain('none')}"
            time.sleep(1)
        time.sleep(5)
        b = brain("nitwit")
        assert "job_site" not in b and '"minecraft:nitwit"' in b, b
