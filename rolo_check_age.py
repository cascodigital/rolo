#!/usr/bin/env python3
"""30-day lazy DNA refresh; does not replace the independent live pulse."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from rolo_common import DB_PATH, DNA_PATH, TIMEZONE, load_db
MAX_AGE_DAYS = 30

def check_age(db_path=DB_PATH, dna_path=DNA_PATH, now=None):
    now = now or datetime.now(ZoneInfo(TIMEZONE))
    try:
        db = load_db(db_path)
        last = datetime.fromisoformat(db['last_update'])
        last = last.replace(tzinfo=now.tzinfo) if last.tzinfo is None else last
        age = (now-last).total_seconds()/86400
        if age < -5/1440:
            return 'INVALID future history update', 10
        if age > MAX_AGE_DAYS:
            return f'STALE {int(age)}', 10
        with open(dna_path, encoding='utf-8') as handle:
            dna = json.load(handle)
        generated = datetime.fromisoformat(dna['generated_at'])
        generated = generated.replace(tzinfo=now.tzinfo) if generated.tzinfo is None else generated
        dna_age = (now-generated).total_seconds()/86400
        if (dna.get('schema_version') != 2 or dna.get('total_tracks_analyzed') != len(db['listens'])
            or dna.get('source_last_update') != db['last_update']
            or not all(isinstance(dna.get(k), list) for k in ('top_dna_weighted', 'current_mood_artists', 'forgotten_gems_artists'))
            or dna_age < -5/1440 or dna_age > MAX_AGE_DAYS):
            return 'STALE DNA integrity/version/date', 10
        return f'FRESH {max(0,int(age))} DNA_OK; pulse independent', 0
    except Exception:
        return 'MISSING_OR_INVALID history/DNA', 10

def main():
    message, status = check_age()
    print(message)
    raise SystemExit(status)

if __name__ == '__main__':
    main()
