<div align="center">

# Rolo: DNA-Driven Music Curation

**Linux music curation automation using listening history and the 40/40/20 rule.**

![Status](https://img.shields.io/badge/Status-Active-16A34A?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-2563EB?style=flat-square)
![Casco Digital](https://img.shields.io/badge/Casco-Digital-111827?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Shell-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white)
![YT Music](https://img.shields.io/badge/YouTube_Music-API-FF0000?style=flat-square&logo=youtubemusic&logoColor=white)

</div>

---

O **Rolo** é uma ferramenta de automação e curadoria musical baseada em inteligência artificial. Ele permite que um agente de IA (como o Gemini ou Claude) analise seu histórico real de audição via ListenBrainz e gere playlists inteligentes no YouTube Music usando o algoritmo de equilíbrio dinâmico **40/40/20**.

Este projeto inclui um servidor **MCP (Model Context Protocol)**, o que significa que você pode dar "poderes" à sua IA favorita para que ela gerencie sua vida musical por você.

## 🏗️ Ciclo de Vida dos Dados (O Fluxo)

O Rolo não trabalha com "achismos". Ele segue um pipeline rigoroso de dados:

1.  **Ingestão (`utils/update_database.sh`):** Coleta até 10.000 registros (listens) do seu perfil no ListenBrainz. Ele é inteligente o suficiente para fazer o append incremental, mantendo seu `history_db.json` sempre fresco.

2.  **Análise (`analysis/analyze_music_dna.py`):** É o cérebro que processa o JSON bruto. Aqui ele aplica o **Linkin Park Cap** (normalização logarítmica para artistas hiper-frequentados) e a **Vacinagem de Duplicatas** (ignora double scrobbles do Last.fm/Pear).

3.  **DNA (`music_dna.json`):** O resultado da análise é um mapa do seu gosto, separando o que você ouve agora, o que você amava mas esqueceu, e o que define seu estilo.

4.  **Criação (`scripts/create_work_playlist.py`):** O motor que consulta esse mapa e monta a playlist final no YouTube Music.

---

## 📻 O Algoritmo 40/40/20

Para evitar que suas playlists fiquem repetitivas ou estranhas, o Rolo força um equilíbrio matemático:

- **40% Nostalgia Real (Forgotten Gems):** O Rolo identifica artistas que estão no seu "Top 100 de todos os tempos", mas que você **não ouviu nenhuma vez nas últimas 1.000 músicas**. Ele resgata essas pérolas para garantir que você não esqueça suas raízes.

- **40% Descoberta Afim (Discovery):** Ele busca artistas novos ou menos ouvidos que compartilham o mesmo DNA técnico dos seus artistas favoritos. É a dose de frescor necessária.

- **20% Vício Atual (Current Mood):** Baseado estritamente nas suas **últimas 500 músicas**. É o que você está martelando no player agora, garantindo que a playlist tenha a sua "vibe" do momento.

---

## 🛠️ Guia de Instalação (Debian/Ubuntu/WSL)

Siga estes passos na ordem exata para evitar erros de permissão ou dependências:

### 1. Preparação do Sistema
Instale as ferramentas de base necessárias para o processamento de JSON e comunicação com APIs:
```bash
sudo apt update && sudo apt install -y python3-venv jq curl
```

### 2. Configuração do Ambiente Python
**AVISO:** Nunca utilize `sudo` para comandos `pip` ou `venv` dentro da sua pasta home.
```bash
# Entre na pasta do projeto
cd ~/rolo

# Criação do ambiente virtual isolado
python3 -m venv .venv

# Ativação do ambiente (Obrigatório em toda nova sessão)
source .venv/bin/activate

# Instalação das bibliotecas necessárias
pip install ytmusicapi requests
```

### 3. Configuração do Histórico (ListenBrainz)
O Rolo precisa de dados para trabalhar. Usamos o ListenBrainz como fonte:
1. Abra o arquivo `utils/update_database.sh` e mude a variável `USER="seu_usuario"` para o seu nome de usuário do ListenBrainz.
2. Dê permissão de execução ao script:
   ```bash
   chmod +x utils/update_database.sh
   ```
3. Execute a primeira sincronização:
   ```bash
   ./utils/update_database.sh
   ```

### 4. Autenticação YouTube Music (F12)
Para o Rolo conseguir criar playlists, ele precisa dos seus cabeçalhos de navegação (Cookies/Auth):
1. Abra o [YouTube Music](https://music.youtube.com) no navegador e faça login.
2. Pressione **F12** > aba **Network** (Rede).
3. Procure por uma requisição chamada **`browse`** (clique em qualquer playlist para forçar a requisição).
4. Em **Request Headers**, clique no botão **"Raw"** e copie **TODO o conteúdo** (exceto a primeira linha que começa com `POST`).
5. No terminal (com o `.venv` ativo), rode:
   ```bash
   ytmusicapi browser
   ```
6. Cole o conteúdo, pressione **ENTER** para criar uma linha vazia e salve com **`CTRL+D`**.
7. O arquivo `browser.json` será gerado na raiz do projeto.

---

## 🤖 Integração com IA (Gemini CLI / Claude Code)

Você pode usar o Rolo como uma "Skill" para o seu agente de IA.

### 1. Configuração de Skill & MCP
- **Skill:** Copie `gemini/SKILL.md` para `~/.gemini/skills/rolo/SKILL.md`.
- **MCP Server:** Adicione o servidor MCP ao seu arquivo de configuração (`~/.gemini/config.json`):

```json
"mcpServers": {
  "rolo": {
    "command": "python3",
    "args": ["/home/seu-user/rolo/gemini/mcp_server.py"]
  }
}
```

Com isso, a IA passa a ter acesso às ferramentas `rolo.sync`, `rolo.analyze` e `rolo.create_playlist`.

### 2. Exemplos de Interação (Vibe Check)
Graças à integração com a Skill e o MCP, você pode pedir coisas como:

- *"Rolo, cria uma playlist para andar de bicicleta na rua enquanto chove e é segunda de manhã, mas eu não fui trabalhar."*
- *"Rolo, estou num mood nostálgico dos anos 90, mas quero descobrir algo novo que eu nunca ouvi."*
- *"Rolo, limpa o meu DNA e foca no que eu ouvi nas últimas 2 horas para o meu treino."*

---

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
Desenvolvido com 🐧 por **Casco Digital** e **Skippy**.
