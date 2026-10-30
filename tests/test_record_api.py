"""tools/record_api.py: download writes the one .aoe2record of the zip of the record API (#4482)."""
import io
import json
import os
import urllib.error
import zipfile

import pytest

from tools import record_api


def zipped(name, data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, data)
    return buf.getvalue()


def test_download_writes_the_record_and_returns_its_path(tmp_path):
    urls = []

    def opener(url):
        urls.append(url)
        return io.BytesIO(zipped("AgeIIDE_Replay_1.aoe2record", b"record bytes"))

    path = record_api.download("123", "456", str(tmp_path), opener=opener)
    assert path == os.path.join(str(tmp_path), "AgeIIDE_Replay_1.aoe2record")
    assert open(path, "rb").read() == b"record bytes"
    assert "gameId=123" in urls[0] and "profileId=456" in urls[0]


def test_a_missing_match_says_that_the_api_keeps_only_recent_games(tmp_path):
    def opener(url):
        raise urllib.error.HTTPError(url, 404, "Match not found.", None, None)

    with pytest.raises(SystemExit, match="only recent games"):
        record_api.download("123", "456", str(tmp_path), opener=opener)


def json_opener(answer, requests):
    def opener(req):
        requests.append(req)
        return io.BytesIO(json.dumps(answer).encode())
    return opener


def test_profiles_returns_the_ids_and_sends_the_name_as_json():
    requests = []
    answer = {"items": [{"rlUserId": 11, "userName": "Ann"}, {"rlUserId": 12, "userName": "Annie"}]}
    assert record_api.profiles("Ann", opener=json_opener(answer, requests)) == [(11, "Ann"), (12, "Annie")]
    assert json.loads(requests[0].data)["searchPlayer"] == "Ann"
    assert requests[0].get_header("Content-type") == "application/json"


def test_matches_returns_the_newest_game_ids_first():
    requests = []
    rows = [{"matchId": str(n), "dateTime": t, "mapType": "Arabia", "civilization": " Franks", "winLoss": "Win"}
            for n, t in ((1, "9/4/2026 4:09:07 AM"), (2, "10/18/2026 8:27:15 PM"), (3, "10/18/2026 8:19:43 PM"))]
    got = record_api.matches(11, 2, opener=json_opener({"matchList": rows}, requests))
    assert [m["matchId"] for m in got] == ["2", "3"]
    assert json.loads(requests[0].data)["profileId"] == 11
    assert requests[0].get_header("Content-type") == "application/json"
    assert record_api.match_line(got[0], 11, "Ann") == "2 11  2026-10-18 20:27  Arabia  Ann (Franks, Win)"


def test_an_empty_answer_gives_no_profile():
    assert record_api.profiles("nobody", opener=lambda req: io.BytesIO(b"")) == []
