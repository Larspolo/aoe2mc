"""Live replay: the production panel above each producing building (#2811, decision #2808: C). Fake RCON."""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [8.0, 8.0], "footprint": [26, 26, 38, 38]}
# Town center 5: 1 villager (25 s), Loom (25 s), 2 villagers.
TIMELINE = [{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 1000, "player": 1, "kind": "research", "objects": [5], "technology": "Loom"},
            {"time": 2000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE",
             "amount": 2}]


def make(more=()):
    d = data(TIMELINE + list(more))
    d["objects"].append(TC)
    return replay.Replay(Fake(), d)


def test_the_first_unit_shows_with_its_queue_and_a_progress_bar():
    r = make()
    (summon,) = r.panel(500)
    assert summon.startswith("summon text_display 32.0 ") and "aoe2mc.panel.5" in summon
    assert '"text": "Villager Male [..........]", "color": "blue"' in summon
    assert r.panel(900) == []                                        # no change: no command
    (merge,) = r.panel(12500)
    assert merge.startswith("data merge entity @e[type=text_display,tag=aoe2mc.panel.5,limit=1] ")
    assert "Villager Male \\u00d73 [|||||.....]" in merge


def test_the_panel_changes_at_the_end_of_an_item_and_goes_when_empty():
    r = make()
    r.panel(500)
    (merge,) = r.panel(30000)
    assert '"Loom [||........]"' in merge
    assert "Villager Male \\u00d72 [|" in r.panel(62500)[0]
    assert r.panel(100000) == ["kill @e[type=text_display,tag=aoe2mc.panel.5]"]
    assert r.panel(110000) == []


def test_the_run_kills_each_panel_at_the_end():
    r = make([{"time": 30000, "player": 1, "kind": "chat", "text": "x"}])
    game = r.game
    now = [0.0]

    def sleep(s):
        now[0] += s
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    sent = game.sent
    assert any("aoe2mc.panel.5" in c and c.startswith("summon") for c in sent)
    assert "kill @e[type=text_display,tag=aoe2mc.panel.5]" in sent


@pytest.mark.mc
def test_the_panel_commands_run_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    r = make()
    with run.Game(world) as game:
        game.command("forceload add 0 0 63 63")
        sel = "@e[type=text_display,tag=aoe2mc.panel.5,limit=1]"
        for t, shown in ((500, "Villager"), (12500, "Villager"), (30000, "Loom"), (100000, None)):
            for c in r.panel(t):
                out = game.command(c)
                assert not any(w in out for w in ("Unknown", "Incorrect", "Expected", "No entity")), (c, out)
            out = game.command(f"data get entity {sel} text")
            assert (shown in out) if shown else "No entity" in out, (t, out)
