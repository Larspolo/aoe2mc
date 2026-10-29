# Environment

The project part of the cloud environment of aoe2mc. `docs/STEERING.md` (generic) points here (#1900).

## Network

The agent starts a headless Minecraft server for tests. For this, the environment allows these hosts
(done in #12):

    piston-meta.mojang.com
    piston-data.mojang.com
    libraries.minecraft.net

The owner allowed more hosts on 2026-10-29. Test from the container on that day:

| Host | Result |
|---|---|
| `minecraft.wiki` | Works (also `?action=raw`). |
| `minecraft.net`, `www.minecraft.net` | Work. |
| `aoe.ms`, `api.ageofempires.com` | Work. `aoe.ms/replay/?gameId=G&profileId=P` redirects to `api.ageofempires.com/api/GameStats/AgeII/GetMatchReplay/?gameId=G&profileId=P&matchId=G`, which sends a zip with one `.aoe2record`. Only recent games: a game of 1 day ago worked, games of 8 weeks ago and of the last hours gave 404 "Match not found.". |
| `data.aoe2companion.com`, `www.aoe2insights.com` | The proxy lets them through. The API and match pages give a Cloudflare 403. |

Find a game: POST JSON to `api.ageofempires.com/api/v2/AgeII/Leaderboard` (`{"region":"7","matchType":"3","consoleMatchType":15,"searchPlayer":"","page":1,"count":10}`, the field `rlUserId` is the profile ID), then to `api.ageofempires.com/api/GameStats/AgeII/GetMatchList` (`{"gamertag":"unknown user","playerNumber":0,"game":"age2","profileId":P,"sortColumn":"dateTime","sortDirection":"DESC","page":1,"recordCount":5,"matchType":"3"}`).

## Setup script

`scripts/cloud-setup.sh` installs Java 25 (the Minecraft 26.3 server, a JDK for the Paper plugin), software Vulkan
and `xdotool` (the client of `tools/mc_shot.py`), the Python packages and the Minecraft and Paper server jars.
