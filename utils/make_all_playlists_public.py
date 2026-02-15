from ytmusicapi import YTMusic
import os

def make_all_public():
    # Tenta browser.json primeiro, depois oauth.json
    auth_file = "browser.json"
    if not os.path.exists(auth_file):
        auth_file = "oauth.json"
        
    if not os.path.exists(auth_file):
        print(f"❌ Arquivo de autenticação (browser.json ou oauth.json) não encontrado.")
        return

    try:
        yt = YTMusic(auth_file)
        playlists = yt.get_library_playlists(limit=100)
        
        print(f"🔄 Encontradas {len(playlists)} playlists. Iniciando conversão para PUBLIC...")
        
        for p in playlists:
            p_id = p['playlistId']
            title = p['title']
            
            # Ignorar playlists de sistema
            if p_id in ['LM', 'SE']:
                continue
                
            try:
                # O status de privacidade não vem no get_library_playlists básico, 
                # então editamos todas para garantir.
                yt.edit_playlist(p_id, privacyStatus='PUBLIC')
                print(f"✅ '{title}' agora é PÚBLICA.")
            except Exception as e:
                print(f"⚠️ Erro ao editar '{title}': {e}")
                
        print("\n🔥 Operação concluída! O mundo agora pode ouvir seu bom (ou duvidoso) gosto musical.")

    except Exception as e:
        print(f"💥 Erro geral: {e}")

if __name__ == "__main__":
    make_all_public()
