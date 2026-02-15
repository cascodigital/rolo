import json
from collections import Counter
import re

import os

# Caminho relativo para o banco de dados
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
db_path = os.path.join(project_root, 'history_db.json')

def get_video_id(url):
    if not url: return None
    match = re.search(r'v=([^&]+)', url)
    return match.group(1) if match else None

try:
    with open(db_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    listens = data.get('listens', [])
    
    # Counter for (track, artist) -> count
    # Also keep a map for (track, artist) -> video_id (most recent or valid one)
    track_counts = Counter()
    track_video_ids = {}

    for listen in listens:
        meta = listen.get('track_metadata', {})
        artist = meta.get('artist_name', 'Unknown')
        track = meta.get('track_name', 'Unknown')
        
        # Skip Linkin Park
        if 'linkin park' in artist.lower():
            continue
            
        key = (track, artist)
        track_counts[key] += 1
        
        # Try to snag a video ID if we don't have one
        if key not in track_video_ids:
            info = meta.get('additional_info', {})
            url = info.get('origin_url', '')
            vid = get_video_id(url)
            if vid:
                track_video_ids[key] = vid

    # Get top 30 (buffer for missing IDs)
    top_tracks = track_counts.most_common(50)
    
    final_list = []
    for (track, artist), count in top_tracks:
        vid = track_video_ids.get((track, artist))
        # If we have a video ID, great. If not, we list it anyway, Rolo can search later.
        # But for this script, let's output what we have.
        final_list.append({
            'title': track,
            'artist': artist,
            'count': count,
            'videoId': vid
        })
        if len(final_list) >= 15:
            break
            
    print(json.dumps(final_list, indent=2))

except Exception as e:
    print(f"Error: {e}")
