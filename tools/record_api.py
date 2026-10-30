#!/usr/bin/env python3
"""
Download the record (.aoe2record) of a recent AoE2 DE match from the record API (#4482, epic #4481).

Usage:
    python3 tools/record_api.py download GAME PROFILE DIR
    python3 tools/record_api.py matches NAME [--count N]      (#4483: the last matches of a player)

The URL redirects to the match replay: the answer is a zip with one .aoe2record file. The API keeps only recent games.
"""
import argparse
import datetime
import io
import json
import os
import urllib.error
import urllib.request
import zipfile

URL = "https://aoe.ms/replay/?gameId={game}&profileId={profile}"
LEADERBOARD = "https://api.ageofempires.com/api/v2/AgeII/Leaderboard"
MATCH_LIST = "https://api.ageofempires.com/api/GameStats/AgeII/GetMatchList"


def post(url, body, opener=urllib.request.urlopen):
    """The JSON answer of a POST of body (JSON) to url, {} for an empty answer (a search with no hit). Without
    Content-Type: application/json the API answers 415."""
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with opener(req) as r:
        return json.loads(r.read() or b"{}")


def profiles(name, opener=urllib.request.urlopen):
    """The (profile ID, user name) of the players of the 1v1 random map leaderboard whose name has name. The answer:
    {"count": n, "items": [{"rlUserId": profile ID, "userName": str, "eloHighest": int, "rank": int, ...}]}."""
    body = {"region": "7", "matchType": "3", "consoleMatchType": 15, "searchPlayer": name, "page": 1, "count": 10}
    return [(i["rlUserId"], i["userName"]) for i in post(LEADERBOARD, body, opener).get("items") or []]


def matches(profile, count, opener=urllib.request.urlopen):
    """The last count matches of the player profile, newest first: dicts with "matchId" (the game ID of download),
    "dateTime" ("10/18/2026 8:27:15 PM", UTC), "mapType", "civilization" and "winLoss". The answer is {"matchList":
    [...]}; it has no names of the other players, does not sort and ignores recordCount (seen 2026-10-30), so this
    function sorts and cuts."""
    body = {"gamertag": "unknown user", "playerNumber": 0, "game": "age2", "profileId": profile,
            "sortColumn": "dateTime", "sortDirection": "DESC", "page": 1, "recordCount": count, "matchType": "3"}
    rows = post(MATCH_LIST, body, opener).get("matchList") or []
    return sorted(rows, key=lambda m: when(m["dateTime"]), reverse=True)[:count]


def when(text):
    """The datetime of a "dateTime" of the match list."""
    return datetime.datetime.strptime(text, "%m/%d/%Y %I:%M:%S %p")


def match_line(m, profile, name):
    """One line of a match, ready to copy: GAME PROFILE  date time  map  name (civilization, result)."""
    return f"{m['matchId']} {profile}  {when(m['dateTime']):%Y-%m-%d %H:%M}  {m['mapType']}  " \
           f"{name} ({m['civilization'].strip()}, {m['winLoss']})"


def download(game, profile, folder, opener=urllib.request.urlopen):
    """Write the .aoe2record of the match game of the player profile into folder and return its path."""
    try:
        with opener(URL.format(game=game, profile=profile)) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(f"No record of match {game}: the API keeps only recent games")
        raise
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = next(n for n in z.namelist() if n.endswith(".aoe2record"))
        path = os.path.join(folder, os.path.basename(name))
        with open(path, "wb") as f:
            f.write(z.read(name))
    return path


def main():
    parser = argparse.ArgumentParser(description="Download the record of a match from the AoE2 record API.")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("download", help="write the .aoe2record of a match into DIR and print its path")
    d.add_argument("game")
    d.add_argument("profile")
    d.add_argument("dir")
    m = sub.add_parser("matches", help="print the last matches of a player name")
    m.add_argument("name")
    m.add_argument("--count", type=int, default=5)
    a = parser.parse_args()
    if a.command == "download":
        print(download(a.game, a.profile, a.dir))
        return
    found = profiles(a.name)
    if not found:
        raise SystemExit(f"No player {a.name}")
    profile, name = next((p for p in found if p[1].lower() == a.name.lower()), found[0])
    for row in matches(profile, a.count):
        print(match_line(row, profile, name))


if __name__ == "__main__":
    main()
