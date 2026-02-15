#!/bin/bash

# Rolo Database Updater (Industrial Linux Version)
# Source: ListenBrainz API

USER="YOUR_LISTENBRAINZ_USER"
TARGET_COUNT=10000
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$PROJECT_ROOT/history_db.json"

echo "--- INICIANDO SYNC DO CEREBRO DO ROLO ($TARGET_COUNT tracks) ---"

# Garante que o arquivo base existe
if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
    echo '{"last_update": "", "count": 0, "listens": []}' > "$DB_PATH"
fi

NEXT_TS=""
CURRENT_COUNT=$(jq '.listens | length' "$DB_PATH" 2>/dev/null || echo 0)

while [ "$CURRENT_COUNT" -lt "$TARGET_COUNT" ]; do
    URL="https://api.listenbrainz.org/1/user/$USER/listens?count=100"
    [ ! -z "$NEXT_TS" ] && URL="$URL&max_ts=$NEXT_TS"

    echo -n "Baixando lote... (Total: $CURRENT_COUNT) "
    
    RESPONSE_TMP=$(mktemp)
    curl -s -f "$URL" > "$RESPONSE_TMP"
    
    if [ $? -ne 0 ]; then
        echo -e "\n❌ Erro na API ou fim do histórico."
        rm -f "$RESPONSE_TMP"
        break
    fi

    NEW_DATA_TMP=$(mktemp)
    jq -c '.payload.listens' "$RESPONSE_TMP" > "$NEW_DATA_TMP"
    
    NEW_COUNT=$(jq '. | length' "$NEW_DATA_TMP" 2>/dev/null || echo 0)
    if [ "$NEW_COUNT" -eq 0 ] || [ "$NEW_COUNT" == "null" ]; then
        echo -e "\n✅ Fim do histórico disponível."
        rm -f "$RESPONSE_TMP" "$NEW_DATA_TMP"
        break
    fi

    # Merge via arquivos (evita Argument list too long)
    TEMP_DB=$(mktemp)
    jq -s '.[0].listens += .[1] | .[0]' "$DB_PATH" "$NEW_DATA_TMP" > "$TEMP_DB" && mv "$TEMP_DB" "$DB_PATH"

    CURRENT_COUNT=$(jq '.listens | length' "$DB_PATH")
    NEXT_TS=$(jq -r '.[-1].listened_at' "$NEW_DATA_TMP")
    
    rm -f "$RESPONSE_TMP" "$NEW_DATA_TMP"
    echo " [OK]"
    sleep 0.2
done

TEMP_FILE=$(mktemp)
jq --arg date "$(date +%Y-%m-%d)" --arg count "$CURRENT_COUNT" '.last_update = $date | .count = ($count|tonumber)' "$DB_PATH" > "$TEMP_FILE" && mv "$TEMP_FILE" "$DB_PATH"

echo -e "\n🔥 Base de dados sincronizada: $DB_PATH"
echo "--- TOP 10 ARTISTAS ---"
jq -r '.listens[].track_metadata.artist_name' "$DB_PATH" | sort | uniq -c | sort -rn | head -n 10
