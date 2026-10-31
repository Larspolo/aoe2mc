"""A Return of Rome record replays with the tables of Antiquity Mode (#4898): game/run.py record_rules reads the data set
of the lobby. The rule modules read their data at import, so the check of the tables runs in one child process."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game")]
import run  # noqa: E402

CODE = r'''
import json, sys
sys.path[:0] = ["game"]
import run, table
table.use(run.record_rules(sys.argv[1]))
print(json.dumps([r["name"] for r in table.load("units.jsonl")]))
'''


def world(tmp_path, dataset):
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"lobby": {"dataset": dataset}}))
    return str(tmp_path)


def names(path):
    env = {k: v for k, v in os.environ.items() if k != "AOE2MC_RULES"}
    r = subprocess.run([sys.executable, "-c", CODE, path], capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode == 0, r.stderr[-2000:]
    return set(json.loads(r.stdout.splitlines()[-1]))


def test_a_return_of_rome_record_uses_the_antiquity_tables(tmp_path):
    (tmp_path / "rome").mkdir()
    (tmp_path / "de").mkdir()
    rome, de = world(tmp_path / "rome", run.ROME), world(tmp_path / "de", "Definitive Edition")
    assert (run.record_rules(rome), run.record_rules(de)) == ("antiquity", "aoe2")
    ancient = {json.loads(s)["name"] for s in open(os.path.join(ROOT, "game/data/antiquity/units.jsonl")) if s.strip()}
    only = ancient - names(de)
    assert only and only <= names(rome)


def test_a_world_with_no_lobby_keeps_the_standard_tables(tmp_path):
    assert run.record_rules(str(tmp_path)) == "aoe2"
