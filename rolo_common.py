"""Shared identity, validation and crash-safe local JSON writes for Rolo."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unicodedata

SKILL_DIR = Path(__file__).resolve().parent
# Data files live next to the scripts unless ROLO_DATA_DIR points elsewhere.
DATA_DIR = Path(os.environ.get('ROLO_DATA_DIR') or SKILL_DIR)
DB_PATH = DATA_DIR / 'history_db.json'
DNA_PATH = DATA_DIR / 'music_dna.json'
# Timezone used for human-readable timestamps (history update, DNA generation).
TIMEZONE = os.environ.get('ROLO_TZ', 'UTC')
LISTENBRAINZ_API = 'https://api.listenbrainz.org/1/user/{user}/listens'


def listens_url():
    """ListenBrainz listens endpoint for ROLO_LISTENBRAINZ_USER (required for network calls)."""
    user = os.environ.get('ROLO_LISTENBRAINZ_USER', '').strip()
    if not user:
        raise RuntimeError('Set ROLO_LISTENBRAINZ_USER to your ListenBrainz username')
    return LISTENBRAINZ_API.format(user=user)

def normalize_name(text):
    decomposed = unicodedata.normalize('NFKD', str(text or '').casefold())
    return ' '.join(''.join(c for c in decomposed if not unicodedata.combining(c)).split())

def artist_key(text):
    return normalize_name(text)

def is_artist_label(text):
    return not artist_key(text) or artist_key(text) in {'music library uploads', 'release'}

def listen_key(listen):
    meta = listen['track_metadata']
    return (listen['listened_at'], artist_key(meta['artist_name']), normalize_name(meta['track_name']))

def clean_listens(listens, now=None):
    """Only merge the same artist+track at the SAME second; repeats remain plays."""
    now = time.time() if now is None else now
    if not isinstance(listens, list):
        raise ValueError('listens must be an array')
    unique = {}
    for listen in listens:
        if not isinstance(listen, dict):
            raise ValueError('Invalid listen object')
        stamp = listen.get('listened_at')
        meta = listen.get('track_metadata')
        if (isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0
                or stamp > now + 300):
            raise ValueError('Invalid or future listen timestamp')
        if not isinstance(meta, dict) or not all(isinstance(meta.get(k), str) and meta[k].strip()
                                                  for k in ('artist_name', 'track_name')):
            raise ValueError('Listen missing artist or track')
        unique.setdefault(listen_key(listen), listen)
    return sorted(unique.values(), key=lambda x: x['listened_at'], reverse=True)

def load_db(path=DB_PATH):
    with open(path, encoding='utf-8') as handle:
        db = json.load(handle)
    if not isinstance(db, dict):
        raise ValueError('Invalid history document')
    listens = clean_listens(db.get('listens'))
    if not listens or db.get('count') != len(db['listens']):
        raise ValueError('Empty history or inconsistent count')
    return {**db, 'listens': listens, 'count': len(listens)}

def atomic_json(path, data, backup=True):
    """Serialize+fsync temp first, copy old snapshot, then single atomic replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if backup and path.exists():
            # The consumed artifact remains in place even if backup creation fails.
            shutil.copy2(path, str(path) + '.bak')
        os.replace(temporary, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
