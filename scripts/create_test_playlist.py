from ytmusicapi import YTMusic
import os

# IDs: Bohemian Rhapsody, Billie Jean, Smells Like Teen Spirit
video_ids = ["yl3TsqL0ZPw", "Kr4EQDVETuA", "ljUtuoFt-8c"]
playlist_title = "Teste do Rolo"
description = "Três pedradas pra testar o sistema. Curadoria: Rolo."

# Tenta achar browser.json ou oauth.json
auth_file = "browser.json"
if not os.path.exists(auth_file):
    auth_file = "oauth.json"

if not os.path.exists(auth_file):
    print("❌ Cadê o browser.json (ou oauth.json)?")
    print("Abra o YouTube Music, pegue os headers no F12 e rode 'ytmusicapi browser-auth'.")
    exit(1)

try:
    print(f"🎧 Logando com {auth_file}...")
    yt = YTMusic(auth_file)
    playlist_id = yt.create_playlist(playlist_title, description, privacy_status="PUBLIC")
    print(f"✅ Playlist '{playlist_title}' criada! ID: {playlist_id}")
    
    status = yt.add_playlist_items(playlist_id, video_ids)
    print(f"🎶 Músicas adicionadas: {status}")
    print("🔥 Tá na mão! Solta o som.")
except Exception as e:
    print(f"💥 Deu ruim: {e}")
