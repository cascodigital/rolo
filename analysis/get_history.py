import requests
import json
import sys

USER = "YOUR_LISTENBRAINZ_USER"
URL = f"https://api.listenbrainz.org/1/user/{USER}/listens?count=50"

try:
    response = requests.get(URL)
    response.raise_for_status()
    data = response.json()
    
    print(f"--- HISTÓRICO RECENTE DE {USER.upper()} ---")
    
    genres = {}
    artists = {}
    
    count = 0
    for listen in data['payload']['listens']:
        track = listen['track_metadata']
        artist = track['artist_name']
        song = track['track_name']
        print(f"- {artist} : {song}")
        
        # Simple stats
        artists[artist] = artists.get(artist, 0) + 1
        count += 1

    print("\n--- TOP ARTISTAS NA AMOSTRA ---")
    sorted_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)[:5]
    for art, qtd in sorted_artists:
        print(f"{art}: {qtd} vezes")

except Exception as e:
    print(f"Erro ao buscar ListenBrainz: {e}")
