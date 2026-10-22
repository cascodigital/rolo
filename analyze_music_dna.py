#!/usr/bin/env python3
"""Lifetime DNA, mood of the last 30 calendar days and absence >=180 days."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import math
import time
from zoneinfo import ZoneInfo
from rolo_common import DB_PATH, DNA_PATH, TIMEZONE, artist_key, is_artist_label, atomic_json, load_db

OUTPUT_PATH = DNA_PATH
MOOD_DAYS = 30
FORGOTTEN_DAYS = 180
LINKIN_PARK_CAP = 150

def squash_weight(count):
    return count if count <= LINKIN_PARK_CAP else LINKIN_PARK_CAP + math.log2(count - LINKIN_PARK_CAP + 1) * 15

def build_summary(db, now=None):
    now = time.time() if now is None else now
    from rolo_common import clean_listens
    listens = clean_listens(db['listens'], now)
    all_artists, recent_artists = Counter(), Counter()
    labels, last_seen = defaultdict(Counter), {}
    excluded = 0
    recent_count = 0
    for listen in listens:
        raw = listen['track_metadata']['artist_name'].strip()
        if is_artist_label(raw):
            excluded += 1
            continue
        key, stamp = artist_key(raw), listen['listened_at']
        labels[key][raw] += 1
        all_artists[key] += 1
        last_seen[key] = max(last_seen.get(key, 0), stamp)
        if now - MOOD_DAYS * 86400 <= stamp <= now:
            recent_artists[key] += 1
            recent_count += 1
    # Prefer the most used spelling; prefer accents when equally frequent.
    names = {key: max(values, key=lambda label: (values[label], sum(ord(c)>127 for c in label), label))
             for key, values in labels.items()}
    ranking = sorted(all_artists, key=lambda key: (-squash_weight(all_artists[key]), names[key]))
    forgotten = [key for key in ranking[:100] if now-last_seen[key] >= FORGOTTEN_DAYS*86400][:15]
    return {
        'schema_version': 2,
        'generated_at': datetime.fromtimestamp(now, ZoneInfo(TIMEZONE)).isoformat(),
        'source_last_update': db.get('last_update'),
        'source_newest_listen': max((l['listened_at'] for l in listens), default=None),
        'total_tracks_analyzed': len(listens),
        'excluded_artist_labels': excluded,
        'mood_window_days': MOOD_DAYS,
        'recent_listens_count': recent_count,
        'forgotten_min_absence_days': FORGOTTEN_DAYS,
        'top_dna_weighted': [{'artist': names[k], 'raw_count': all_artists[k],
                              'weighted_score': round(squash_weight(all_artists[k]),2)} for k in ranking[:20]],
        'current_mood_artists': [names[k] for k,_ in recent_artists.most_common(10)],
        'forgotten_gems_artists': [names[k] for k in forgotten],
        'forgotten_gems_details': [{'artist': names[k], 'days_absent': int((now-last_seen[k])/86400)} for k in forgotten],
        'analysis_notes': ['Artist names normalized by Unicode, accents, case and whitespace',
                           'Exact timestamp + artist + track duplicates removed; legitimate repeats retained',
                           'Mood: last 30 days relative to generation; no old-play fallback',
                           'Forgotten: lifetime top 100 absent for at least 180 days',
                           'Upload/release labels excluded; high play counts weighted logarithmically']
    }

def analyze():
    db = load_db(DB_PATH)
    summary = build_summary(db)
    atomic_json(OUTPUT_PATH, summary)
    print(f'DNA_OK tracks={summary["total_tracks_analyzed"]} recent_30d={summary["recent_listens_count"]} -> {OUTPUT_PATH}')

if __name__ == '__main__':
    analyze()
