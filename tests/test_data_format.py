"""Each line of a .jsonl data file is in the format of json.dumps(..., ensure_ascii=False): a script can then write back
all lines, and the diff has only its own change (#1934, #2034)."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_each_line_is_in_the_json_dumps_format():
    wrong = []
    for path in sorted(glob.glob(os.path.join(ROOT, "game", "data", "*.jsonl")) + glob.glob(os.path.join(ROOT, "data", "*.jsonl"))):
        for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            if line and json.dumps(json.loads(line), ensure_ascii=False) != line:
                wrong.append(f"{os.path.relpath(path, ROOT)}:{n}")
    assert not wrong, f"write these lines with json.dumps(row, ensure_ascii=False): {wrong}"
