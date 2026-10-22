#!/usr/bin/env python3
"""Incremental ListenBrainz merge. Failed or ambiguous pagination never publishes."""
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import requests
from rolo_common import DB_PATH, TIMEZONE, atomic_json, clean_listens, listen_key, listens_url, load_db

TARGET_COUNT = 10000
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
MAX_PAGES = 2000

def request_page(params):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(listens_url(), params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return clean_listens(response.json()['payload']['listens'])
        except Exception:
            if attempt == MAX_RETRIES-1:
                raise RuntimeError('ListenBrainz request/validation failed after retries') from None
            time.sleep(2*(attempt+1))

def fetch_all_listens(existing=None, fetch_page=None):
    """Returns listens and proof metadata. Raises on incomplete/ambiguous sync.

    With history: fetch through its newest timestamp and require identity overlap.
    Without history: load a 10k window or prove natural exhaustion. Initial 10k
    means a complete requested window, never a claim of complete lifetime history.
    """
    existing = clean_listens(existing or [])
    fetch_page = request_page if fetch_page is None else fetch_page
    watermark = existing[0]['listened_at'] if existing else None
    known = {listen_key(l) for l in existing}
    downloaded, next_ts = [], None
    for pages in range(1, MAX_PAGES+1):
        params = {'count': PAGE_SIZE}
        if next_ts is not None:
            params['max_ts'] = next_ts
        page = clean_listens(fetch_page(params))
        if not page:
            if existing and not any(listen_key(l) in known for l in downloaded):
                raise RuntimeError('History ended without confirming overlap with local snapshot')
            return clean_listens(downloaded), {'pages': pages, 'reached_end': True, 'watermark_crossed': bool(existing)}
        if next_ts is not None and any(l['listened_at'] >= next_ts for l in page):
            raise RuntimeError('Pagination did not advance strictly; original snapshot preserved')
        downloaded.extend(page)
        oldest = page[-1]['listened_at']
        overlap = any(listen_key(l) in known for l in downloaded) if existing else False
        # Strictly cross watermark so all same-second new listens get a chance.
        if existing and oldest < watermark:
            if not overlap:
                raise RuntimeError('Watermark crossed without matching any local listen')
            return clean_listens(downloaded), {'pages': pages, 'reached_end': False, 'watermark_crossed': True}
        if not existing and len(clean_listens(downloaded)) >= TARGET_COUNT:
            return clean_listens(downloaded), {'pages': pages, 'reached_end': False, 'watermark_crossed': False}
        # max_ts is exclusive. A saturated timestamp could hide events; fail closed.
        if len(page) >= PAGE_SIZE and page[0]['listened_at'] == oldest:
            raise RuntimeError('More than one full page at one timestamp; cannot safely paginate')
        next_ts = oldest
    raise RuntimeError('Pagination safety limit reached; original snapshot preserved')

def sync(db_path=DB_PATH, fetch_page=None):
    from pathlib import Path
    db_path = Path(db_path)
    old = load_db(db_path) if db_path.exists() else None
    listens, proof = fetch_all_listens(old['listens'] if old else [], fetch_page)
    merged = clean_listens(listens + (old['listens'] if old else []))
    if not merged:
        raise RuntimeError('No listens returned; original snapshot preserved')
    stamp = datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    result = {**(old or {}), 'last_update': stamp, 'count': len(merged), 'listens': merged,
              'sync': {'complete': True, 'mode': 'incremental' if old else 'initial_window',
                       'initial_target': TARGET_COUNT, 'fetched': len(listens),
                       'history_complete': bool(proof['reached_end'] or (old or {}).get('sync', {}).get('history_complete')),
                       **proof}}
    atomic_json(db_path, result)
    print(f'SYNC_OK count={len(merged)} fetched={len(listens)} pages={proof["pages"]} mode={result["sync"]["mode"]}')
    return result

def main():
    try:
        sync()
    except Exception as exc:
        print(f'SYNC_FAILED {exc}')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
