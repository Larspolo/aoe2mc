# Environment

The project part of the cloud environment of aoe2mc. `framework/docs/STEERING.md` (generic) points here (#1900).

## Network

`scripts/allowed-domains.txt` is the list of the "Allowed domains" of the cloud environment: one host per line,
no comments, so that the owner can paste the whole file. The Mojang hosts are for the headless Minecraft server of the
tests (#12), the Paper and Gradle hosts for the game program and its plugin.

When a ticket needs a new host:
1. Add the host to `scripts/allowed-domains.txt` in the PR of the ticket (one line, no other change).
2. Make a `needs-human` ticket (P1, size:S, `## For the owner`, Kind: setting) that asks the owner to paste the whole
   file again (the steps of `framework/docs/STEERING.md`, section "Network for the tests"), if no open ticket asks it already.
3. Until the owner pasted it, the host is blocked: continue with other work.

A `needs-human` ticket that only one account can do (a setup script or a host of its cloud environment) also
mentions the GitHub login of that account: `agent_config.login(account)` gives it (`account()` is the run's account,
the owner when the account has no table in `agent.toml`, #4243).

Tests from the container on 2026-10-29: the first when the owner allowed the first hosts after the Mojang hosts, the
second after the paste of the whole file (#4182, the proxy let all 22 hosts through):

| Host | Result |
|---|---|
| `minecraft.wiki` | Works (also `?action=raw`). |
| `minecraft.net` | Works (308). |
| `www.minecraft.net` | Worked in the first test. In the second test the connection opens, but the site sends no data in 20 s (HTTP/2 `INTERNAL_ERROR`, HTTP/1.1 time-out). Use `minecraft.net`. |
| `aoe.ms`, `api.ageofempires.com` | Work. `aoe.ms/replay/?gameId=G&profileId=P` redirects to `api.ageofempires.com/api/GameStats/AgeII/GetMatchReplay/?gameId=G&profileId=P&matchId=G`, which sends a zip with one `.aoe2record`. Only recent games: a game of 1 day ago worked, games of 8 weeks ago and of the last hours gave 404 "Match not found.". |
| `data.aoe2companion.com`, `www.aoe2insights.com` | The proxy lets them through. The API and match pages give a Cloudflare 403. |
| `ageofempires.fandom.com` | Cloudflare 403 ("Just a moment..."). Use `tools/refimage.py` (MediaWiki API). |
| `aoe2.heavengames.com` | HTTPS fails: the certificate does not match the host name. Use `http://` (301). |
| `aok.heavengames.com`, `steamcommunity.com`, `papermc.io`, `repo.papermc.io`, `services.gradle.org`, `plugins.gradle.org` | Work (200). |

Find a game: POST JSON to `api.ageofempires.com/api/v2/AgeII/Leaderboard` (`{"region":"7","matchType":"3","consoleMatchType":15,"searchPlayer":"","page":1,"count":10}`, the field `rlUserId` is the profile ID), then to `api.ageofempires.com/api/GameStats/AgeII/GetMatchList` (`{"gamertag":"unknown user","playerNumber":0,"game":"age2","profileId":P,"sortColumn":"dateTime","sortDirection":"DESC","page":1,"recordCount":5,"matchType":"3"}`).

## Setup script

`scripts/cloud-setup.sh` installs Java 25 (the Minecraft 26.3 server, a JDK for the Paper plugin), software Vulkan
and `xdotool` (the client of `tools/mc_shot.py`), the Python packages and the Minecraft and Paper server jars.
