import json
import math
import os
from collections import Counter
from datetime import datetime

# Configurações
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "history_db.json")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "music_dna.json")
RECENT_THRESHOLD = 500  # Últimas 500 músicas definem o "mood"
FORGOTTEN_LIMIT = 1000  # Se não ouviu nas últimas 1000, é uma "joia esquecida"
LINKIN_PARK_CAP = 150   # Onde a curva de peso começa a achatar

def squash_weight(count):
    """
    Aplica uma curva logarítmica para achatar artistas com muitos plays.
    Se count > CAP, o peso cresce muito devagar.
    """
    if count <= LINKIN_PARK_CAP:
        return count
    return LINKIN_PARK_CAP + (math.log2(count - LINKIN_PARK_CAP + 1) * 15)

def analyze():
    if not os.path.exists(DB_PATH):
        print(f"Erro: {DB_PATH} não encontrado.")
        return

    with open(DB_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    listens = db.get('listens', [])
    total_listens = len(listens)
    
    # 1. Contagem Geral e Recente com De-duplicação
    all_artists = Counter()
    recent_artists = Counter()
    
    # Artistas nas últimas 1000 músicas (para detectar o que NÃO está aqui)
    last_1000_artists = set()
    
    # Para evitar double scrobbling (mesma música/artista no mesmo timestamp)
    seen_listens = set()

    for i, listen in enumerate(listens):
        meta = listen.get('track_metadata', {})
        artist = meta.get('artist_name')
        track = meta.get('track_name', '')
        ts = listen.get('listened_at') # Timestamp do ListenBrainz
        
        if not artist: continue
        
        # Chave de unicidade: Artista + Primeiro 10 caracteres da música + Timestamp
        # (Usamos apenas o início da música para ignorar variações com duração no título)
        unique_key = f"{artist}|{track[:10]}|{ts}"
        if unique_key in seen_listens:
            continue
        seen_listens.add(unique_key)
        
        all_artists[artist] += 1
        
        if i < RECENT_THRESHOLD:
            recent_artists[artist] += 1
        
        if i < FORGOTTEN_LIMIT:
            last_1000_artists.add(artist)

    # 2. Processar DNA com Normalização (Squashing)
    dna_list = []
    for artist, count in all_artists.items():
        weight = squash_weight(count)
        dna_list.append({
            "artist": artist,
            "raw_count": count,
            "weighted_score": round(weight, 2)
        })

    # Top 50 por peso
    dna_list.sort(key=lambda x: x['weighted_score'], reverse=True)
    top_dna = dna_list[:50]

    # 3. Detectar Joias Esquecidas (Forgotten Gems)
    # Candidatos: Top 100 artistas vitalícios que NÃO aparecem nas últimas 1000 músicas
    top_100_lifetime = [x['artist'] for x in dna_list[:100]]
    forgotten_gems = [a for a in top_100_lifetime if a not in last_1000_artists][:15]

    # 4. Detectar Mood Atual (Top Artistas Recentes)
    current_mood = [a for a, c in recent_artists.most_common(10)]

    # 5. Resumo Executivo para o Rolo
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_tracks_analyzed": total_listens,
        "top_dna_weighted": top_dna[:20], # Top 20 para o contexto não explodir
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

    print(f"Análise de DNA concluída. Resultado em: {OUTPUT_PATH}")

if __name__ == "__main__":
    analyze()
