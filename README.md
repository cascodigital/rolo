# Rolo: DNA-Driven Music Curation (Linux Edition) 🎧

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Author](https://img.shields.io/badge/Author-Casco%20Digital-orange)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Shell-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white)
![YT Music](https://img.shields.io/badge/YouTube_Music-API-FF0000?style=flat-square&logo=youtubemusic&logoColor=white)

Sub-mente de entretenimento projetada para analisar o DNA musical de um usuário via ListenBrainz e gerar curadorias no YouTube Music usando o algoritmo de equilíbrio dinâmico **40/40/20**.

## 🏗️ Ciclo de Vida dos Dados (O Fluxo)

O Rolo não trabalha com "achismos". Ele segue um pipeline rigoroso de dados:

1.  **Ingestão (`utils/update_database.sh`):** Coleta até 10.000 registros (listens) do seu perfil no ListenBrainz. Ele é inteligente o suficiente para fazer o append incremental, mantendo seu `history_db.json` sempre fresco.
2.  **Análise (`analysis/analyze_music_dna.py`):** É o cérebro que processa o JSON bruto. Aqui ele aplica o **Linkin Park Cap** (normalização logarítmica para artistas hiper-frequentados) e a **Vacinagem de Duplicatas** (ignora double scrobbles do Last.fm/Pear).
3.  **DNA (`music_dna.json`):** O resultado da análise é um mapa do seu gosto, separando o que você ouve agora, o que você amava mas esqueceu, e o que define seu estilo.
4.  **Criação (`scripts/create_work_playlist.py`):** O motor que consulta esse mapa e monta a playlist final no YouTube Music.

## 📻 O Algoritmo 40/40/20

Para evitar que suas playlists fiquem repetitivas ou estranhas, o Rolo força um equilíbrio matemático:

*   **40% Nostalgia Real (Forgotten Gems):** O Rolo identifica artistas que estão no seu "Top 100 de todos os tempos", mas que você **não ouviu nenhuma vez nas últimas 1.000 músicas**. Ele resgata essas pérolas para garantir que você não esqueça suas raízes.
*   **40% Descoberta Afim (Discovery):** Ele busca artistas novos ou menos ouvidos que compartilham o mesmo DNA técnico dos seus artistas favoritos. É a dose de frescor necessária.
*   **20% Vício Atual (Current Mood):** Baseado estritamente nas suas **últimas 500 músicas**. É o que você está martelando no player agora, garantindo que a playlist tenha a sua "vibe" do momento.

## 🛠️ Instalação (Debian/Ubuntu/WSL)

### 1. Dependências do Sistema
```bash
sudo apt update && sudo apt install -y python3-venv jq curl
```

### 2. Ambiente Virtual & Dependências Python
**IMPORTANTE:** Nunca use `sudo` para instalar pacotes Python na sua home.
```bash
cd ~/rolo
python3 -m venv .venv
source .venv/bin/activate
pip install ytmusicapi requests
```

### 3. Autenticação YouTube Music (F12)
1. Abra o [YouTube Music](https://music.youtube.com) > F12 > Network.
2. Busque por uma requisição `browse` e copie os **Request Headers** (Raw).
3. No terminal (venv ativo), rode: `ytmusicapi browser`.
4. Cole o conteúdo (sem a linha do POST), dê **ENTER** e salve com **CTRL+D**.

## 🚀 Como Atualizar e Rodar

Sempre execute o ciclo completo para manter o DNA atualizado:

```bash
source .venv/bin/activate

# 1. Sincroniza o histórico (ListenBrainz -> local)
./utils/update_database.sh

# 2. Processa o DNA (Analisa pesos e tendências)
python3 analysis/analyze_music_dna.py

# 3. Entrega a curadoria (Cria no YT Music)
python3 scripts/create_work_playlist.py
```

---
Desenvolvido com 🐧 por **Casco Digital** e **Skippy (Gemini CLI)**.
