import json
import math
import os
from collections import Counter
from datetime import datetime

# Settings
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "history_db.json")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "music_dna.json")
RECENT_THRESHOLD = 500  # The last 500 tracks define the current "mood"
FORGOTTEN_LIMIT = 1000  # Not heard in the last 1000 tracks = "forgotten gem"
LINKIN_PARK_CAP = 150   # Play count where the weight curve starts to flatten

def squash_weight(count):
    """
    Apply a logarithmic curve to flatten artists with very high play counts.
    Above CAP, the weight grows very slowly.
    """
    if count <= LINKIN_PARK_CAP:
        return count
    return LINKIN_PARK_CAP + (math.log2(count - LINKIN_PARK_CAP + 1) * 15)

def analyze():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    with open(DB_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    listens = db.get('listens', [])
    total_listens = len(listens)
    
    # 1. Overall and recent counts, with de-duplication
    all_artists = Counter()
    recent_artists = Counter()
    
    # Artists in the last 1000 tracks (used to detect who is NOT here)
    last_1000_artists = set()
    
    # Avoid double scrobbles (same track/artist at the same timestamp)
    seen_listens = set()

    for i, listen in enumerate(listens):
        meta = listen.get('track_metadata', {})
        artist = meta.get('artist_name')
        track = meta.get('track_name', '')
        ts = listen.get('listened_at') # ListenBrainz timestamp
        
        if not artist: continue
        
        # Uniqueness key: artist + first 10 characters of the track + timestamp
        # (only the start of the title is used, to ignore variants that append a duration)
        unique_key = f"{artist}|{track[:10]}|{ts}"
        if unique_key in seen_listens:
            continue
        seen_listens.add(unique_key)
        
        all_artists[artist] += 1
        
        if i < RECENT_THRESHOLD:
            recent_artists[artist] += 1
        
        if i < FORGOTTEN_LIMIT:
            last_1000_artists.add(artist)

    # 2. Build the DNA with normalization (squashing)
    dna_list = []
    for artist, count in all_artists.items():
        weight = squash_weight(count)
        dna_list.append({
            "artist": artist,
            "raw_count": count,
            "weighted_score": round(weight, 2)
        })

    # Top 50 by weight
    dna_list.sort(key=lambda x: x['weighted_score'], reverse=True)
    top_dna = dna_list[:50]

    # 3. Detect forgotten gems
    # Candidates: top 100 lifetime artists that do NOT appear in the last 1000 tracks
    top_100_lifetime = [x['artist'] for x in dna_list[:100]]
    forgotten_gems = [a for a in top_100_lifetime if a not in last_1000_artists][:15]

    # 4. Detect current mood (top recent artists)
    current_mood = [a for a, c in recent_artists.most_common(10)]

    # 5. Summary consumed by the Rolo agent
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_tracks_analyzed": total_listens,
        "top_dna_weighted": top_dna[:20], # Top 20 only, to keep the LLM context small
        "current_mood_artists": current_mood,
        "forgotten_gems_artists": forgotten_gems,
        "analysis_notes": [
            "Linkin Park weight normalized",
            f"Mood based on last {RECENT_THRESHOLD} tracks",
            f"Forgotten gems: artists from top 100 not heard in last {FORGOTTEN_LIMIT} tracks"
        ]
    }

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"DNA analysis complete. Output: {OUTPUT_PATH}")

if __name__ == "__main__":
    analyze()
