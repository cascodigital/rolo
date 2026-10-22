from ytmusicapi import YTMusic
import sys
import os

# Search queries: example tracks (hardcoded sample list)
queries = [
    "Arctic Monkeys Do I Wanna Know?",
    "The Strokes Reptilia",
    "Tame Impala The Less I Know The Better",
    "Royal Blood Figure It Out",
    "Legião Urbana Tempo Perdido",
    "Tears For Fears Head Over Heels",
    "Queens of the Stone Age No One Knows",
    "Capital Inicial Primeiros Erros"
]

print("Rolo: starting playlist creation...")

# Authentication: browser.json in the project root, with oauth.json as fallback
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
auth_file = os.path.join(project_root, "browser.json")

if not os.path.exists(auth_file):
    auth_file = os.path.join(project_root, "oauth.json")

if not os.path.exists(auth_file):
    print(f"Error: no authentication file found in {project_root}")
    print("Follow the README instructions to generate browser.json from the browser request headers.")
    sys.exit(1)

try:
    print(f"Using credentials: {auth_file}")
    yt = YTMusic(auth_file)
    
    # 1. Create Playlist
    playlist_id = yt.create_playlist("Trabalho Focado (Rolo's Mix)", "Playlist pra focar no trampo. Curadoria do Rolo.", privacy_status="PUBLIC")
    print(f"Playlist created. ID: {playlist_id}")
    
    video_ids = []
    
    # 2. Search and Add
    print("Searching tracks...")
    for q in queries:
        search_results = yt.search(q, filter="songs")
        if search_results:
            video_id = search_results[0]['videoId']
            title = search_results[0]['title']
            video_ids.append(video_id)
            print(f"  -> Found: {title}")
        else:
            print(f"  [!] Not found: {q}")

    # 3. Populate
    if video_ids:
        yt.add_playlist_items(playlist_id, video_ids)
        print(f"{len(video_ids)} tracks added.")
    else:
        print("No tracks found.")

except Exception as e:
    print(f"Fatal error: {e}")
