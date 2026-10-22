#!/bin/bash
# Refresh the local snapshots (history_db.json, music_dna.json) when they are stale.
# Impact: local JSON files only. Rollback: the previous versions are kept as *.bak.
# Usage: ./rolo_update.sh [--force]
set -euo pipefail
export TZ="${ROLO_TZ:-UTC}"
SKILL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${ROLO_DATA_DIR:-$SKILL_DIR}"
LOG="${ROLO_LOG:-${TMPDIR:-/tmp}/rolo_update.log}"
if [[ "${1:-}" != "--force" ]] && python3 "$SKILL_DIR/rolo_check_age.py"; then exit 0; fi
exec 9>"$DATA_DIR/.update.lock"
flock -n 9 || { echo "UPDATE_BUSY"; exit 1; }
python3 "$SKILL_DIR/update_rolo_db.py" 2>&1 | tee -a "$LOG"
python3 "$SKILL_DIR/analyze_music_dna.py" 2>&1 | tee -a "$LOG"
python3 "$SKILL_DIR/rolo_check_age.py"
