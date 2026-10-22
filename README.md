# rolo

Music curation toolkit that turns a ListenBrainz listening history into a taste profile an AI agent uses to build YouTube Music playlists.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.12+-3776AB) ![Status](https://img.shields.io/badge/status-experimental-orange)

## Overview

Streaming-service recommendations tend to loop over the same few artists and ignore what a listener loved years
ago. Rolo pulls up to 10,000 listens from ListenBrainz, condenses them into a compact `music_dna.json` profile
(weighted favorites, current mood, forgotten favorites) and hands that profile to an LLM agent (Gemini CLI or
Claude Code). The agent then picks tracks with a 40/40/20 mix and creates the playlist on YouTube Music.

## Features

- Syncs up to 10,000 listens from the public ListenBrainz API into a local `history_db.json`, paging backwards by timestamp.
- Builds a taste profile: top 20 artists by weighted score, the 10 most-played artists in the last 500 listens, and up to 15 top-100 artists absent from the last 1,000 listens.
- Flattens over-represented artists with a logarithmic weight cap so one artist cannot dominate the profile.
- Drops double scrobbles (same artist, same title prefix, same timestamp).
- Lists "forgotten gems" (artists with 3+ plays not heard in 6 months) and top tracks with their YouTube video IDs.
- Creates public YouTube Music playlists from search queries via `ytmusicapi`.
- Ships an agent persona prompt (`gemini/SKILL.md`) and a small stdio command server so an agent can run sync, analysis and playlist creation.

## How it works

```
ListenBrainz API --> utils/update_database.sh --> history_db.json
                                                      |
                                    analysis/analyze_music_dna.py
                                                      |
                                               music_dna.json
                                                      |
                     LLM agent (gemini/SKILL.md persona, 40/40/20 rule)
                                                      |
                              ytmusicapi (browser.json auth) --> YouTube Music playlist
```

- **Ingestion** (`utils/update_database.sh`): bash + `curl` + `jq`. Requests 100 listens per call with `max_ts`
  paging and merges batches through temp files to avoid shell argument-length limits. Listens are stored newest first.
- **Analysis** (`analysis/analyze_music_dna.py`): counts per artist after de-duplication. Above 150 plays the
  weight becomes `150 + 15 * log2(count - 149)`. Writes `music_dna.json` with `top_dna_weighted`,
  `current_mood_artists` and `forgotten_gems_artists`. Only the top 20 artists are written to keep the agent's context small.
- **Curation**: the 40/40/20 rule is applied by the agent, guided by `gemini/SKILL.md`:
  40% forgotten gems, 40% discovery of artists similar to the weighted top, 20% current mood.
  The persona prompt is intentionally written in Brazilian Portuguese, the language of its end user.
- **Delivery**: `ytmusicapi` authenticated with browser request headers (`browser.json`).
- **Agent bridge** (`gemini/mcp_server.py`): reads one JSON object per line on stdin and answers on stdout.
  Methods `rolo.sync`, `rolo.analyze` and `rolo.create_playlist` run the three scripts above.

## Requirements

- Linux (Debian/Ubuntu/WSL tested), bash, `curl`, `jq`
- Python 3.12+ with `ytmusicapi` and `requests`
- A ListenBrainz account with scrobbled history (public listens; no token needed)
- A YouTube Music account (browser request headers for `ytmusicapi`)
- Optional: Gemini CLI or Claude Code to act as the curation agent

## Quick start

1. Install system packages and the Python environment:
   ```bash
   sudo apt update && sudo apt install -y python3-venv jq curl
   cd rolo
   python3 -m venv .venv
   source .venv/bin/activate
   pip install ytmusicapi requests
   ```
2. Set your ListenBrainz username in `utils/update_database.sh` (`USER="YOUR_LISTENBRAINZ_USER"`), then sync:
   ```bash
   chmod +x utils/update_database.sh
   ./utils/update_database.sh
   ```
3. Create YouTube Music credentials. Open https://music.youtube.com logged in, press F12, open the Network tab,
   click any playlist and select a `browse` request. Copy the raw request headers (everything after the first
   `POST` line), then run the command below, paste, press Enter on an empty line and finish with `Ctrl+D`.
   Save the result as `browser.json` in the project root.
   ```bash
   ytmusicapi browser
   ```
4. Build the taste profile and inspect it:
   ```bash
   python3 analysis/analyze_music_dna.py
   cat music_dna.json
   ```

## Configuration

| Variable / key | Required | Default | Description |
| --- | --- | --- | --- |
| `USER` in `utils/update_database.sh` | Yes | `YOUR_LISTENBRAINZ_USER` | ListenBrainz username to sync |
| `TARGET_COUNT` in `utils/update_database.sh` | No | `10000` | Number of listens to keep locally |
| `USER` in `analysis/get_history.py` | For that script | `YOUR_LISTENBRAINZ_USER` | Username for the quick 50-listen preview |
| `RECENT_THRESHOLD` in `analysis/analyze_music_dna.py` | No | `500` | Listens that define the current mood |
| `FORGOTTEN_LIMIT` in `analysis/analyze_music_dna.py` | No | `1000` | Window an artist must be absent from to count as forgotten |
| `LINKIN_PARK_CAP` in `analysis/analyze_music_dna.py` | No | `150` | Play count where weight flattening starts |
| `browser.json` (or `oauth.json`) | Yes, for playlists | none | `ytmusicapi` credentials; git-ignored |

## Usage

Full cycle:

```bash
source .venv/bin/activate
./utils/update_database.sh                 # ListenBrainz -> history_db.json
python3 analysis/analyze_music_dna.py      # history_db.json -> music_dna.json
python3 scripts/create_work_playlist.py    # create a playlist on YouTube Music
```

| Script | What it does | Changes state? |
| --- | --- | --- |
| `utils/update_database.sh` | Syncs listens from ListenBrainz into `history_db.json` and prints the top 10 artists | Writes local file |
| `analysis/analyze_music_dna.py` | Builds `music_dna.json` from the history | Writes local file |
| `analysis/analyze_forgotten_gems.py` | Prints 20 random artists (with best track and video ID) not heard in 6 months | No |
| `analysis/get_favorites.py` | Prints the 15 most-played tracks with video IDs, excluding Linkin Park | No |
| `analysis/get_history.py` | Prints the last 50 listens and top 5 artists from the API | No |
| `scripts/create_work_playlist.py` | Searches a fixed list of example queries and creates a public playlist | Yes, YouTube Music |
| `scripts/create_test_playlist.py` | Creates a public 3-track test playlist | Yes, YouTube Music |
| `utils/make_all_playlists_public.py` | Sets every library playlist (except system ones) to PUBLIC | Yes, YouTube Music |

### Agent integration (Gemini CLI / Claude Code)

- Copy `gemini/SKILL.md` to `~/.gemini/skills/rolo/SKILL.md`.
- Register the command server in the agent configuration:
  ```json
  "mcpServers": {
    "rolo": {
      "command": "python3",
      "args": ["/path/to/rolo/gemini/mcp_server.py"]
    }
  }
  ```
- Requests look like `{"id": 1, "method": "rolo.analyze"}`. The response contains the script's stdout, stderr and exit code.

## Limitations

- `gemini/mcp_server.py` is a minimal line-based JSON protocol, not a spec-compliant MCP server
  (no JSON-RPC 2.0 initialize handshake or `tools/list`). Agents that require full MCP will not detect its tools.
- `scripts/create_work_playlist.py` uses a hardcoded query list; it does not read `music_dna.json`.
  Track selection based on the profile is done by the agent.
- `analysis/analyze_forgotten_gems.py` uses a 6-month time window, while `music_dna.json` uses the last-1,000-listens window; results differ.
- Configuration lives in script constants, not a config file or environment variables.
- `create_test_playlist.py` and `make_all_playlists_public.py` look for credentials in the current directory; run them from the project root.
- Browser-header authentication expires and must be regenerated periodically.
- Re-running the sync after reaching `TARGET_COUNT` does not fetch newer listens.

## License

MIT — see [LICENSE](LICENSE).
