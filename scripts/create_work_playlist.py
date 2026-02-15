from ytmusicapi import YTMusic
import sys
import os

# IDs: Pedradas do DNA (Exemplo)
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

print("🎧 Rolo na área! Iniciando os trabalhos...")

# Lógica de Autenticação Robusta
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
auth_file = os.path.join(project_root, "browser.json")

if not os.path.exists(auth_file):
    # Tenta oauth.json como backup
    auth_file = os.path.join(project_root, "oauth.json")

if not os.path.exists(auth_file):
    print(f"❌ Erro: Nenhum arquivo de autenticação encontrado em {project_root}")
    print("Siga as instruções do README para gerar o browser.json via F12.")
    sys.exit(1)

try:
    print(f"🔐 Usando credenciais: {auth_file}")
    yt = YTMusic(auth_file)
    
    # 1. Create Playlist
    playlist_id = yt.create_playlist("Trabalho Focado (Rolo's Mix)", "Playlist pra focar no trampo. Curadoria do Rolo.", privacy_status="PUBLIC")
    print(f"✅ Playlist criada! ID: {playlist_id}")
    
    video_ids = []
    
    # 2. Search and Add
    print("🔍 Buscando as pedradas...")
    for q in queries:
        search_results = yt.search(q, filter="songs")
        if search_results:
            video_id = search_results[0]['videoId']
            title = search_results[0]['title']
            video_ids.append(video_id)
            print(f"  -> Encontrada: {title}")
        else:
            print(f"  ⚠️ Não achei: {q}")

    # 3. Populate
    if video_ids:
        yt.add_playlist_items(playlist_id, video_ids)
        print(f"🔥 {len(video_ids)} faixas adicionadas com sucesso!")
        print("🎶 Agora é só dar o play e produzir!")
    else:
        print("❌ Nenhuma música encontrada.")

except Exception as e:
    print(f"💥 Erro crítico: {e}")
