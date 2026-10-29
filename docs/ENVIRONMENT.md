# Environment

The project part of the cloud environment of aoe2mc. `docs/STEERING.md` (generic) points here (#1900).

## Network

`scripts/allowed-domains.txt` is the list of the "Allowed domains" of the cloud environment: one host per line,
no comments, so that the owner can paste the whole file. The Mojang hosts are for the headless Minecraft server of the
tests (#12), the Paper and Gradle hosts for the game program and its plugin.

When a ticket needs a new host:
1. Add the host to `scripts/allowed-domains.txt` in the PR of the ticket (one line, no other change).
2. Make a `needs-human` ticket (P1, size:S, `## For the owner`, Kind: setting) that asks the owner to paste the whole
   file again (the steps of `docs/STEERING.md`, section "Network for the tests"), if no open ticket asks it already.
3. Until the owner pasted it, the host is blocked: continue with other work.

Test from the container on 2026-10-29, when the owner allowed the first hosts after the Mojang hosts:

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
