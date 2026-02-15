import json
import time
import random
from datetime import datetime

import os

# Configurações
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "history_db.json")
SIX_MONTHS_AGO = int(time.time()) - (180 * 24 * 60 * 60)

def analyze():
    print("Carregando o banco de dados (pode demorar um tiquinho)...")
    try:
        with open(DB_PATH, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erro ao ler o DB: {e}")
        return

    listens = data.get('listens', [])
    print(f"Total de listens analisados: {len(listens)}")

    artist_stats = {}

    for listen in listens:
        try:
            ts = listen['listened_at']
            track_meta = listen['track_metadata']
            artist = track_meta['artist_name']
            track = track_meta['track_name']
            
            # Try to get video_id
            origin_url = track_meta.get('additional_info', {}).get('origin_url', '')
            video_id = None
            if 'v=' in origin_url:
                video_id = origin_url.split('v=')[1].split('&')[0]
                
        except KeyError:
            continue

        if artist not in artist_stats:
            artist_stats[artist] = {
                'count': 0,
                'last_listen': 0,
                'top_tracks': {},
                'video_ids': {}
            }
        
        artist_stats[artist]['count'] += 1
        if ts > artist_stats[artist]['last_listen']:
            artist_stats[artist]['last_listen'] = ts
        
        # Count tracks per artist to pick the best one later
        if track not in artist_stats[artist]['top_tracks']:
             artist_stats[artist]['top_tracks'][track] = 0
        artist_stats[artist]['top_tracks'][track] += 1
        
        if video_id:
            artist_stats[artist]['video_ids'][track] = video_id

    # Filter: Forgotten Gems
    # Criteria: 
    # 1. Last listen < 6 months ago
    # 2. Total plays > 3
    
    forgotten_gems = []

    for artist, stats in artist_stats.items():
        if stats['last_listen'] < SIX_MONTHS_AGO and stats['count'] >= 3:
            # Find most played track for this artist
            best_track = max(stats['top_tracks'], key=stats['top_tracks'].get)
            
            # Get video_id for the best track if available
            vid = stats['video_ids'].get(best_track)
            
            # Convert timestamp to readable date
            last_date = datetime.fromtimestamp(stats['last_listen']).strftime('%d/%m/%Y')
            
            # Only include if we have a video ID or if you want to fall back to searching later.
            # Rolo prefers precision, so let's prefer ones with IDs, but include others if needed.
            # For now, let's keep all and mark if they have ID.
            
            forgotten_gems.append({
                'artist': artist,
                'track': best_track,
                'last_listen_date': last_date,
                'count': stats['count'],
                'video_id': vid
            })

    # Sort by 'count' to get the ones you liked the most first
    forgotten_gems.sort(key=lambda x: x['count'], reverse=True)
    top_candidates = forgotten_gems[:100] # Pool of top 100 forgotten artists
    
    if not top_candidates:
        print("Nenhuma pérola esquecida encontrada com os critérios atuais.")
        return

    random.shuffle(top_candidates)
    selection = top_candidates[:20]

    print(json.dumps(selection, indent=4))

if __name__ == "__main__":
    analyze()