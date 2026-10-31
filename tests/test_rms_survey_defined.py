import os
import sys

import rmap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rms_survey  # noqa: E402


def test_labels_of_the_converter_are_not_undefined(tmp_path):
    text = "if REGICIDE\nelseif LUDIKRIS_MAP\nelseif 2_PLAYER_GAME\nelseif DARK_AGE_START\nendif\n"
    (tmp_path / "own.rms").write_text(text, encoding="utf-8")
    assert set(rms_survey.undefined(str(tmp_path))) == {"DARK_AGE_START"}


def test_each_lobby_label_turns_on_its_if_block():
    labels = sorted(rmap.lobby_labels())
    text = "".join(f"if {label}\n<seen_{label}>\nendif\n" for label in labels)
    seen = set()
    teams = [[None]] + [[t] * m for t in range(1, 5) for m in range(1, 9)] + [[1, 2], [1, 2, 3], [1, 2, 3, 4] * 2]
    settings = [{"players": len(t), "teams": t} for t in teams]
    settings += [{"players": p} for p in range(1, 9)]
    settings += [{"mode": m} for m in rmap.MODE_LABELS] + [{"size": s} for s in rmap.MAP_SIZES.values()]
    settings += [{"labels": [label]} for label in rmap.LOBBY_LABELS.values()]
    settings += [{"players": 8, "teams": [i % 4 + 1 if i < 4 else None for i in range(8)]}]
    for kw in settings:
        warnings = []
        rmap.generate(text, 1, warn=warnings.append, **kw)
        seen |= {w.split()[0][1:-1].removeprefix("seen_") for w in warnings if w.startswith("<seen_")}
    assert seen == set(labels)
