# rolo

Music curation toolkit that turns a ListenBrainz listening history into a taste profile and a validation gate
an AI agent uses to build YouTube Music playlists.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.12+-3776AB) ![Status](https://img.shields.io/badge/status-active-green)

## Overview

Streaming-service recommendations tend to loop over the same few artists and ignore what a listener loved years
ago, and an LLM asked to "make a playlist from my history" will happily invent facts about that history. Rolo keeps
a local, incrementally synced copy of the ListenBrainz history, condenses it into a compact `music_dna.json`
profile, and gives the agent a small JSON context plus a deterministic validator. The agent picks tracks with a
40/40/20 mix; `rolo_curate.py` checks every claim (nostalgia, discovery, current) against the data before and after
the playlist is created on YouTube Music.

## Features

- Syncs ListenBrainz listens incrementally into `history_db.json`, proving overlap with the local snapshot and
  failing closed (no write) on ambiguous or interrupted pagination.
- Writes every JSON file atomically (temp file + fsync + rename) and keeps the previous version as `*.bak`.
- Builds a taste profile: top 20 artists by log-capped weight, current-mood artists from the last 30 days, and
  lifetime top-100 artists absent for 180+ days.
- Normalizes artist identity (Unicode, accents, case, whitespace) and drops upload labels; only exact
  timestamp + artist + track duplicates are merged, so legitimate repeats still count.
- Produces a compact curation context: nostalgia and current candidates, explicit feedback and deliveries of the
  last 30 days, merged with a live 30-day "pulse" fetched from the API.
- Validates a playlist plan: 40/40/20 quotas (largest-remainder rounding), max two tracks per artist, no duplicates,
  no repeats within 30 days, feedback blocks, and a readback check after creation.
- Records explicit like / dislike / skip feedback (dry run unless `--apply`).
- Refreshes lazily: `rolo_check_age.py` reports when history or DNA is older than 30 days or out of sync.

## How it works

```
ListenBrainz API --> update_rolo_db.py --> history_db.json --> analyze_music_dna.py --> music_dna.json
        |                (rolo_update.sh, flock, lazy via rolo_check_age.py)                  |
        +--- live 30-day pulse --------------------+                                          |
                                                   v                                          v
                         rolo_curate.py context  <-- feedback.json -->  rolo_curate.py validate / record
                                   |                                              ^
                                   v                                              |
              LLM agent (40/40/20 rule) --> YouTube Music (create + get_playlist readback)
```

- **Shared core** (`rolo_common.py`): identity normalization, listen validation (rejects future or malformed
  timestamps), crash-safe `atomic_json`, and path/timezone/user configuration from environment variables.
- **Sync** (`update_rolo_db.py`): pages backwards 100 listens at a time with `max_ts`. With an existing history it
  stops after strictly crossing the newest local timestamp and requires at least one identical listen; without one
  it loads a 10,000-listen window. A full page inside one second, a non-advancing cursor or a missing overlap aborts
  the sync and leaves the snapshot untouched. Prints `SYNC_OK ...` or `SYNC_FAILED ...`.
- **Analysis** (`analyze_music_dna.py`): above 150 plays the weight becomes `150 + 15 * log2(count - 149)`.
  Writes schema version 2 with `top_dna_weighted`, `current_mood_artists`, `forgotten_gems_artists` and
  provenance fields (`source_last_update`, `total_tracks_analyzed`) that `rolo_check_age.py` uses as an integrity check.
- **Curation gate** (`rolo_curate.py`): `context` returns at most 30 candidates per bucket so the agent's context
  stays small. `validate` checks a manifest; `record` additionally requires a readback whose ID, count, order and
  track identities match the plan, and is idempotent per playlist ID. `delivery` reports whether a validated
  delivery was recorded for a playlist since a given timestamp, so other automations can verify a job.
  "Discovery" means absent from the available history, not proof the track was never heard.
- **Scrobbler watchdog** (`rolo_check_scrobbler.py`): delegates to an external command and maps its status marker
  to exit codes, so silence or a missing marker counts as failure.
- **Agent persona** (`gemini/SKILL.md`): workflow prompt for Gemini CLI or Claude Code. It is intentionally written
  in Brazilian Portuguese, the language of its end user. `gemini/mcp_server.py` is a small stdio command bridge.

## Requirements

- Linux (Debian/Ubuntu/WSL tested) with bash and `flock` (util-linux)
- Python 3.12+ with `requests` and `ytmusicapi`
- A ListenBrainz account with scrobbled history (public listens; no token needed)
- A YouTube Music account (browser request headers for `ytmusicapi`) for the playlist scripts
- Optional: an agent with a YouTube Music tool set (search, create playlist, get playlist) to do the curation
- Optional: an external scrobbler watchdog command for `rolo_check_scrobbler.py`

## Quick start

1. Create the Python environment:
   ```bash
   cd rolo
   python3 -m venv .venv
   source .venv/bin/activate
   pip install requests ytmusicapi
   ```
2. Set your ListenBrainz username and run the first sync plus analysis:
   ```bash
   export ROLO_LISTENBRAINZ_USER=your_listenbrainz_user
   export ROLO_TZ=America/New_York   # optional, any IANA timezone
   ./rolo_update.sh --force
   ```
3. Check freshness and print the curation context:
   ```bash
   python3 rolo_check_age.py          # FRESH ... DNA_OK; exit 0
   python3 rolo_curate.py context
   ```
4. For the playlist scripts, create YouTube Music credentials. Open https://music.youtube.com logged in, press F12,
   open the Network tab, click any playlist and select a `browse` request. Copy the raw request headers, run the
   command below, paste, press Enter on an empty line and finish with `Ctrl+D`. Save the result as `browser.json`
   in the project root.
   ```bash
   ytmusicapi browser
   ```

## Configuration

| Variable / key | Required | Default | Description |
| --- | --- | --- | --- |
| `ROLO_LISTENBRAINZ_USER` | Yes, for sync and pulse | none | ListenBrainz username whose listens are read |
| `ROLO_DATA_DIR` | No | project root | Directory for `history_db.json`, `music_dna.json`, `feedback.json` and lock files (core pipeline only) |
| `ROLO_TZ` | No | `UTC` | IANA timezone for human-readable timestamps |
| `ROLO_FALLBACK_SSH_HOST` | No | none | SSH host used to fetch the pulse with `curl` when the direct request fails |
| `ROLO_SCROBBLER_CHECK_CMD` | For the watchdog | none | Shell command that prints the `VIGIA_SCROBBLER` marker line (see below) |
| `ROLO_LOG` | No | `$TMPDIR/rolo_update.log` | Log file appended by `rolo_update.sh` |
| `TARGET_COUNT` in `update_rolo_db.py` | No | `10000` | Size of the initial history window |
| `MOOD_DAYS` / `FORGOTTEN_DAYS` in `analyze_music_dna.py` | No | `30` / `180` | Current-mood window and minimum absence for forgotten artists |
| `LINKIN_PARK_CAP` in `analyze_music_dna.py` | No | `150` | Play count where weight flattening starts |
| `MAX_AGE_DAYS` in `rolo_check_age.py` | No | `30` | Age after which history/DNA is considered stale |
| `browser.json` (or `oauth.json`) | Yes, for playlist scripts | none | `ytmusicapi` credentials; git-ignored |

The watchdog command must print one line in the format
`VIGIA_SCROBBLER status=<STATUS> horas=<hours> detalhe="<text>"` (the field names are a contract with the external
script). `OK`/`OK_LB_FORA` exit 0 (`ALIVE`), `STALE` exits 22 (`DEGRADED`), `AUTH_BROKEN` exits 21 (`AUTH_DEAD`),
anything else exits 20 (`DEAD`).

## Usage

Curation cycle driven by an agent:

```bash
./rolo_update.sh                                   # no-op when fresh; syncs + re-analyzes when stale
python3 rolo_curate.py context                     # JSON context for the agent
python3 rolo_curate.py validate --manifest /tmp/rolo-plan.json
# agent creates the playlist, saves get_playlist output and adds playlist_id to the manifest
python3 rolo_curate.py record --manifest /tmp/rolo-plan.json --readback /tmp/rolo-readback.json --apply
python3 rolo_curate.py feedback --artist 'Artist' --title 'Track' --verdict dislike --apply
python3 rolo_curate.py delivery --playlist-id PLxxxx --since 1767225600
```

Manifest format (`mode` is `mix` for the 40/40/20 rule, or `custom` with a `reason` and `custom` categories):

```json
{
  "count": 1,
  "mode": "mix",
  "tracks": [
    {"videoId": "dQw4w9WgXcQ", "title": "Exact title", "artists": ["Artist"], "category": "nostalgia"}
  ]
}
```

`rolo_curate.py` always prints JSON and exits non-zero when `ok` is false. Feedback: `dislike` blocks a track (or
the whole artist when `--title` is omitted), `skip` blocks it for 30 days, a later `like` on the same scope reverses
a block.

| Script | What it does | Changes state? |
| --- | --- | --- |
| `rolo_update.sh [--force]` | Runs sync + analysis under a lock when stale (or always with `--force`) | Writes local files |
| `update_rolo_db.py` | Incremental ListenBrainz sync into `history_db.json` | Writes local file |
| `analyze_music_dna.py` | Builds `music_dna.json` from the history | Writes local file |
| `rolo_check_age.py` | Exit 0 when history and DNA are fresh and consistent, 10 otherwise | No |
| `rolo_check_scrobbler.py` | Runs the external watchdog and maps its status to exit codes | No |
| `rolo_curate.py context / validate / delivery` | Curation context, plan validation, delivery lookup | No |
| `rolo_curate.py feedback / record --apply` | Stores feedback or a verified delivery in `feedback.json` | Writes local file |
| `analysis/analyze_forgotten_gems.py` | Prints 20 random artists (with best track and video ID) not heard in 6 months | No |
| `analysis/get_favorites.py` | Prints the 15 most-played tracks with video IDs, excluding Linkin Park | No |
| `analysis/get_history.py` | Prints the last 50 listens and top 5 artists from the API | No |
| `scripts/create_work_playlist.py` | Searches a fixed list of example queries and creates a public playlist | Yes, YouTube Music |
| `scripts/create_test_playlist.py` | Creates a public 3-track test playlist | Yes, YouTube Music |
| `utils/make_all_playlists_public.py` | Sets every library playlist (except system ones) to PUBLIC | Yes, YouTube Music |

Run the offline test suite (no network needed):

```bash
python3 -m unittest discover -s tests -v
```

### Agent integration (Gemini CLI / Claude Code)

- Copy `gemini/SKILL.md` into the agent's skill folder and run the commands from the project root.
- Register the command bridge in the agent configuration:
  ```json
  "mcpServers": {
    "rolo": {
      "command": "python3",
      "args": ["/path/to/rolo/gemini/mcp_server.py"]
    }
  }
  ```
- Requests look like `{"id": 1, "method": "rolo.context"}`. Methods: `rolo.sync` (`rolo_update.sh --force`),
  `rolo.analyze`, `rolo.context`, `rolo.create_playlist`. The response contains stdout, stderr and the exit code.

## Limitations

- Rolo never writes to YouTube Music by itself in the curation flow; creating the playlist and saving the readback
  is the agent's job.
- The initial sync loads a 10,000-listen window, not the full lifetime history; later syncs only add newer listens.
- `gemini/mcp_server.py` is a minimal line-based JSON protocol, not a spec-compliant MCP server
  (no JSON-RPC 2.0 initialize handshake or `tools/list`).
- `rolo_check_scrobbler.py` ships no watchdog of its own; without `ROLO_SCROBBLER_CHECK_CMD` it always reports `DEAD`.
- The helper scripts in `analysis/`, `scripts/` and `utils/` read files from the project root and ignore
  `ROLO_DATA_DIR`; `get_history.py` has its own `USER` constant.
- `scripts/create_work_playlist.py` uses a hardcoded query list; it does not read `music_dna.json`.
- Browser-header authentication expires and must be regenerated periodically.

## License

MIT — see [LICENSE](LICENSE).
