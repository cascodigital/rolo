# Rolo: DNA-Driven Music Curation (Linux Edition) 🎧

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Author](https://img.shields.io/badge/Author-Casco%20Digital-orange)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Shell-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white)
![YT Music](https://img.shields.io/badge/YouTube_Music-API-FF0000?style=flat-square&logo=youtubemusic&logoColor=white)

Sub-mente de entretenimento projetada para analisar o DNA musical de um usuário via ListenBrainz e gerar curadorias no YouTube Music usando a regra **40/40/20**.

## 🏗️ Arquitetura de Dados

1.  **Ingestão (Bash + jq):** `utils/update_database.sh` coleta seu histórico do ListenBrainz.
2.  **Processamento (Python):** `analysis/analyze_music_dna.py` gera o perfil de gosto.
3.  **Execução (Python):** Scripts em `scripts/` montam as playlists.

## 📂 Estrutura do Repositório

```
rolo/
├── analysis/          # Motores de DNA e Processamento
├── gemini/            # Integração com IA (Skills e MCP)
├── scripts/           # Geração de Playlists no YouTube Music
├── utils/             # Ingestão (Bash) e Manutenção
└── docs/              # Snapshot das playlists geradas
```

## 🛠️ Instalação (Debian/Ubuntu/WSL)

### 1. Dependências do Sistema
```bash
sudo apt update && sudo apt install -y python3-venv jq curl
```

### 2. Ambiente Virtual & Dependências Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ytmusicapi requests
```

### 3. Configuração do ListenBrainz
- Edite `utils/update_database.sh` e mude o `USER="seu_usuario"`.
- Dê permissão: `chmod +x utils/update_database.sh`.
- Execute a coleta: `./utils/update_database.sh`.

### 4. Autenticação YouTube Music (Método F12)
1. Abra o [YouTube Music](https://music.youtube.com) > F12 > aba Network.
2. Busque por uma requisição `browse` e copie os **Request Headers** (Raw).
3. No terminal (venv ativo), rode: `ytmusicapi browser`.
4. Cole o conteúdo, dê **ENTER** e salve com **CTRL+D**. O arquivo `browser.json` será gerado.

---

## 🤖 Integração com IA (Gemini CLI)

Você pode usar o Rolo como uma "Skill" para o seu agente de IA.

### 1. Instale o Gemini CLI
```bash
npm install -g @google/gemini-cli
```

### 2. Configure a Skill
Copie o conteúdo de `gemini/SKILL.md` para a pasta de skills do seu agente (geralmente `~/.gemini/skills/rolo/SKILL.md`). A partir daí, você pode pedir para a IA:
> *"Skippy, aja como o Rolo e crie uma playlist baseada no meu DNA musical atual."*

---

## 🚀 Uso Diário

```bash
source .venv/bin/activate

# 1. Sincroniza DNA (Bash)
./utils/update_database.sh

# 2. Analisa DNA (Python)
python3 analysis/analyze_music_dna.py

# 3. Cria Playlist (Python)
python3 scripts/create_work_playlist.py
```

## ⚠️ Avisos e Segurança
- **Duplicatas:** O script de análise possui lógica nativa para filtrar "Double Scrobbling" (comum em quem usa Last.fm + ListenBrainz).
- **Linkin Park Cap:** Para evitar dominância de um único artista, aplicamos uma curva logarítmica para normalizar o peso de artistas com centenas de plays.

---
Desenvolvido com 🐧 por **Casco Digital**.
