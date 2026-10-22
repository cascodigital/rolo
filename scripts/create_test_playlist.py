from ytmusicapi import YTMusic
import os

# IDs: Bohemian Rhapsody, Billie Jean, Smells Like Teen Spirit
video_ids = ["yl3TsqL0ZPw", "Kr4EQDVETuA", "ljUtuoFt-8c"]
playlist_title = "Teste do Rolo"
description = "Três pedradas pra testar o sistema. Curadoria: Rolo."

# Look for browser.json, then oauth.json (current directory)
auth_file = "browser.json"
if not os.path.exists(auth_file):
    auth_file = "oauth.json"

if not os.path.exists(auth_file):
    print("Error: browser.json (or oauth.json) not found.")
    print("Open YouTube Music, copy the request headers from DevTools (F12) and run 'ytmusicapi browser'.")
    exit(1)

try:
    print(f"Authenticating with {auth_file}...")
    yt = YTMusic(auth_file)
    playlist_id = yt.create_playlist(playlist_title, description, privacy_status="PUBLIC")
    print(f"Playlist '{playlist_title}' created. ID: {playlist_id}")
    
    status = yt.add_playlist_items(playlist_id, video_ids)
    print(f"Tracks added: {status}")
    print("Done.")
except Exception as e:
    print(f"Error: {e}")
