"""Each sound of the game program plays on the Paper server (#3503): the "select" and "order" sounds of
game/data/sounds.jsonl and train.EVENT_SOUNDS, with the category of the game program. /playsound answers
"Played sound" only when a player hears it, so a real client is online. It answers so also for an unknown name:
mcvalid.sound_error checks the names against the sound list of 26.3."""
import shutil

import mcvalid
import pytest

from game import train


def commands():
    """The playsound commands of the game program: voice sounds (train.py, gather.py) and event sounds (master)."""
    out = [f"execute at aoe2mc run playsound minecraft:{v[k]} voice aoe2mc ~ ~ ~ 1 {v['pitch']}"
           for v in train.SOUNDS.values() for k in ("select", "order") if k in v]
    return out + [f"execute at aoe2mc run playsound {s} master aoe2mc ~ ~ ~ 1 1" for s in train.EVENT_SOUNDS.values()]


def test_each_sound_of_the_data_file_has_a_command():
    cmds = commands()
    assert len(cmds) == sum(("select" in v) + ("order" in v) for v in train.SOUNDS.values()) + len(train.EVENT_SOUNDS)
    assert all(c.split()[5].startswith("minecraft:") and mcvalid.sound_error(c.split()[5]) is None for c in cmds)


@pytest.mark.mc
def test_each_sound_plays_for_a_player(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        assert not [c for c in commands() if mcvalid.sound_error(c.split()[5])]
        bad = {c: a for c in commands() if "Played sound" not in (a := game.command(c))}
    assert not bad, bad
