"""game/run.py: the key values of a campaign scenario (storage aoe2mc:keys, trigger effect "Store Key Value") go into
the next scenario, as in AoE2 DE; progress.json keeps them for a later start (#3508)."""
import os

from nbtlib import load

from game import run


def world(tmp_path, name, values=None):
    w = tmp_path / name
    w.mkdir()
    if values is not None:
        run.put_keys(str(w), values)
    return str(w)


def stored(w):
    return {k: int(v) for k, v in load(os.path.join(w, run.STORAGE))["data"]["contents"]["keys"]["values"].items()}


def test_a_key_of_the_old_world_goes_into_a_next_world_with_no_storage(tmp_path):
    old, new = world(tmp_path, "a", {"gold": 5}), world(tmp_path, "b")
    run.carry_keys(old, new)
    assert stored(new) == {"gold": 5}


def test_a_key_of_both_worlds_takes_the_old_value_and_a_key_of_the_next_world_stays(tmp_path):
    old, new = world(tmp_path, "a", {"gold": 5, "wood": 1}), world(tmp_path, "b", {"gold": 2, "stone": 7})
    run.carry_keys(old, new)
    assert stored(new) == {"gold": 5, "wood": 1, "stone": 7}


def test_progress_keeps_the_keys_and_the_won_scenarios(tmp_path):
    run.write_progress(str(tmp_path), keys={"gold": 5})
    run.write_progress(str(tmp_path), won=[1])
    assert run.campaign_keys(str(tmp_path)) == {"gold": 5} and run.progress(str(tmp_path)) == [1]
