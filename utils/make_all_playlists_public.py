from ytmusicapi import YTMusic
import os

def make_all_public():
    # Try browser.json first, then oauth.json (current directory)
    auth_file = "browser.json"
    if not os.path.exists(auth_file):
        auth_file = "oauth.json"
        
    if not os.path.exists(auth_file):
        print("Error: authentication file (browser.json or oauth.json) not found.")
        return

    try:
        yt = YTMusic(auth_file)
        playlists = yt.get_library_playlists(limit=100)
        
        print(f"Found {len(playlists)} playlists. Setting them to PUBLIC...")
        
        for p in playlists:
            p_id = p['playlistId']
            title = p['title']
            
            # Skip system playlists (Liked Music, Episodes for Later)
            if p_id in ['LM', 'SE']:
                continue
                
            try:
                # get_library_playlists does not return privacy status,
                # so every playlist is edited.
                yt.edit_playlist(p_id, privacyStatus='PUBLIC')
                print(f"'{title}' is now PUBLIC.")
            except Exception as e:
                print(f"[!] Failed to edit '{title}': {e}")
                
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    make_all_public()
