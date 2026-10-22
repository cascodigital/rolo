#!/usr/bin/env python3
"""Rolo curation gate: context, explicit feedback and delivery verification. Never writes to YouTube Music."""
import argparse
from collections import Counter
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests
from rolo_common import (DATA_DIR, TIMEZONE, artist_key, normalize_name, is_artist_label, clean_listens,
                         atomic_json, listens_url, load_db)

ROOT = DATA_DIR
DAY = 86400
TZ = ZoneInfo(TIMEZONE)
# Optional SSH host used as a second network route when the direct ListenBrainz call fails.
FALLBACK_SSH_HOST = os.environ.get("ROLO_FALLBACK_SSH_HOST", "").strip()


def local_time(ts):
    return datetime.fromtimestamp(ts, TZ).isoformat()


def state():
    p = ROOT / "feedback.json"
    if not p.exists():
        return {"version": 1, "feedback": [], "delivered": []}
    data = json.loads(p.read_text())
    if data.get("version") != 1 or not isinstance(data.get("feedback"), list) or not isinstance(data.get("delivered"), list):
        raise ValueError("feedback.json is invalid; it will not be overwritten")
    return data


def track_key(track):
    artists = track.get("artists", [])
    if not artists or not all(isinstance(a, str) and a.strip() for a in artists):
        raise ValueError("track has no artist list")
    title = track.get("title", "")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("track has no title")
    return (artist_key(artists[0]), normalize_name(title))


def from_listen(listen):
    m = listen["track_metadata"]
    info = m.get("additional_info", {})
    origin = info.get("origin_url", "")
    video = parse_qs(urlparse(origin).query).get("v", [None])[0]
    if not video and "youtu.be/" in origin:
        video = urlparse(origin).path.strip("/")
    return {"artists": [m["artist_name"]], "title": m["track_name"], "videoId": video}


def fetch_pulse():
    """30-day window. Retries through ROLO_FALLBACK_SSH_HOST (if set) when the direct route fails."""
    url = listens_url()
    result, cursor, route = [], None, "direct"
    now = int(time.time())
    complete = False
    with requests.Session() as session:
        for _ in range(10):
            params = {"count": 100}
            if cursor is not None:
                params["max_ts"] = cursor
            try:
                response = session.get(url, params=params, timeout=12)
                response.raise_for_status()
                page = response.json()["payload"]["listens"]
            except (requests.RequestException, KeyError, ValueError):
                if not FALLBACK_SSH_HOST:
                    raise
                route = "ssh:" + FALLBACK_SSH_HOST
                target = requests.Request("GET", url, params=params).prepare().url
                response = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", FALLBACK_SSH_HOST,
                                           "curl -fsS --max-time 15 '" + target + "'"],
                                          capture_output=True, text=True, timeout=25, check=True)
                page = json.loads(response.stdout)["payload"]["listens"]
            if not isinstance(page, list):
                raise ValueError("ListenBrainz returned no listens array")
            if not page:
                complete = True
                break
            result.extend(page)
            oldest = min(x["listened_at"] for x in page)
            if oldest <= now - 30 * DAY:
                complete = True
                break
            if cursor is not None and oldest >= cursor:
                raise ValueError("pulse pagination did not advance")
            if len(page) >= 100 and max(x["listened_at"] for x in page) == oldest:
                raise ValueError("full page within one second; pulse cannot be considered complete")
            # ListenBrainz max_ts is exclusive: subtracting 1 would skip a second.
            cursor = oldest
    return {"fetched_at": now, "route": route, "complete_30d": complete, "listens": result}


def history(pulse):
    db = load_db(ROOT / "history_db.json")
    combined = clean_listens(db["listens"] + pulse["listens"])
    stats = {}
    for listen in combined:
        t = from_listen(listen)
        if is_artist_label(t["artists"][0]):
            continue
        key = track_key(t)
        item = stats.setdefault(key, {**t, "plays": 0, "recent_plays": 0, "last_listened_at": 0})
        item["plays"] += 1
        if listen["listened_at"] >= time.time() - 30 * DAY:
            item["recent_plays"] += 1
        if listen["listened_at"] >= item["last_listened_at"]:
            item.update(t, last_listened_at=listen["listened_at"])
    return db, stats


def latest_feedback(data):
    result = {}
    for f in data["feedback"]:
        result[(f["artist_key"], f.get("title_key", ""))] = f
    return result


def rejected(track, data, now):
    track_key(track)
    rules = latest_feedback(data)
    title = normalize_name(track["title"])
    for artist in track["artists"]:
        for scope in ((artist_key(artist), ""), (artist_key(artist), title)):
            f = rules.get(scope)
            if f and (f["verdict"] == "dislike" or (f["verdict"] == "skip" and now - f["at"] < 30 * DAY)):
                return True
    return False


def recent_deliveries(data, now):
    keys, videos = set(), set()
    for delivery in data["delivered"]:
        if now - delivery["at"] < 30 * DAY:
            for t in delivery["tracks"]:
                keys.add(track_key(t))
                videos.add(t["videoId"])
    return keys, videos


def context(pulse):
    now = int(time.time())
    db, stats = history(pulse)
    data = state()
    recent_keys, recent_videos = recent_deliveries(data, now)
    eligible = [x for x in stats.values() if not rejected(x, data, now)]
    nostalgia = [x for x in eligible if now - x["last_listened_at"] >= 180 * DAY
                 and track_key(x) not in recent_keys and x.get("videoId") not in recent_videos]
    current = [x for x in eligible if now - x["last_listened_at"] <= 30 * DAY
               and track_key(x) not in recent_keys and x.get("videoId") not in recent_videos]
    dna = json.loads((ROOT / "music_dna.json").read_text())
    def compact(xs, order="plays"):
        return [{**x, "last_listened_local": local_time(x["last_listened_at"])}
                for x in sorted(xs, key=lambda x: x[order], reverse=True)[:30]]
    return {"ok": True, "data": {"history_updated": db.get("last_update"),
            "history_events": len(db["listens"]), "pulse_events": len(pulse["listens"]),
            "pulse_fetched_local": local_time(pulse["fetched_at"]), "pulse_complete_30d": pulse["complete_30d"],
            "latest_listen_local": local_time(max(x["listened_at"] for x in pulse["listens"])) if pulse["listens"] else None,
            "dna": dna.get("top_dna_weighted", []), "nostalgia_candidates": compact(nostalgia),
            "current_candidates": compact(current, "recent_plays"), "feedback": list(latest_feedback(data).values()),
            "recent_deliveries": [{"playlist_id": d["playlist_id"], "tracks": d["tracks"]}
                                  for d in data["delivered"] if now - d["at"] < 30 * DAY]}}


def quotas(n):
    weights = {"nostalgia": .4, "discovery": .4, "current": .2}
    result = {k: int(n * w) for k, w in weights.items()}
    for k in sorted(weights, key=lambda k: n * weights[k] - result[k], reverse=True)[:n - sum(result.values())]:
        result[k] += 1
    return result


def validate(manifest, pulse, data, allow_repeat=False, readback=None):
    now = int(time.time())
    _, stats = history(pulse)
    tracks = manifest.get("tracks", [])
    errors, warnings = [], []
    if not tracks or manifest.get("count") != len(tracks):
        errors.append("count must match a non-empty track list")
    if not pulse.get("complete_30d") or now - pulse["fetched_at"] > 3600 or pulse["fetched_at"] > now + 300:
        errors.append("pulse is incomplete or was not captured within the last hour")
    keys, videos, artists, categories = set(), set(), Counter(), Counter()
    past_keys, past_videos = recent_deliveries(data, now)
    for i, t in enumerate(tracks, 1):
        key = track_key(t)
        video = t.get("videoId", "")
        if not isinstance(video, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
            errors.append(f"track {i}: invalid videoId")
        if key in keys or video in videos:
            errors.append(f"track {i}: duplicate")
        keys.add(key)
        videos.add(video)
        artists.update(set(artist_key(a) for a in t["artists"]))
        if rejected(t, data, now):
            errors.append(f"track {i}: rejected by feedback")
        if any(is_artist_label(a) for a in t["artists"]):
            errors.append(f"track {i}: upload label does not identify an artist")
        if not allow_repeat and (key in past_keys or video in past_videos):
            errors.append(f"track {i}: delivered in the last 30 days")
        found = stats.get(key)
        category = t.get("category")
        categories[category] += 1
        if category == "discovery" and found:
            errors.append(f"track {i}: discovery already exists in the available history")
        elif category == "nostalgia" and (not found or now - found["last_listened_at"] < 180 * DAY):
            errors.append(f"track {i}: nostalgia without a proven 180-day absence")
        elif category == "current" and (not found or now - found["last_listened_at"] > 30 * DAY):
            errors.append(f"track {i}: current pick without a listen in the last 30 days")
        elif category not in ("discovery", "nostalgia", "current", "custom"):
            errors.append(f"track {i}: invalid category")
    if manifest.get("mode", "mix") == "mix":
        if dict(categories) != quotas(len(tracks)):
            errors.append(f"40/40/20 ratio: expected {quotas(len(tracks))}, got {dict(categories)}")
        if any(v > 2 for v in artists.values()):
            errors.append("mix has more than two tracks by the same artist")
    elif manifest.get("mode") != "custom" or not manifest.get("reason"):
        errors.append("custom mode requires a reason quoting the explicit request that changed the formula")
    if readback is not None:
        actual = readback.get("tracks", [])
        if readback.get("id") != manifest.get("playlist_id"):
            errors.append("playlist_id differs from the readback")
        if [x.get("videoId") for x in actual] != [x.get("videoId") for x in tracks]:
            errors.append("readback differs from the planned tracks and order")
        if int(readback.get("trackCount", -1)) != len(tracks):
            errors.append("readback total count differs from the plan")
        for expected, actual_track in zip(tracks, actual):
            if track_key(expected) != track_key(actual_track):
                errors.append("readback title/artist differs from the plan")
    warnings.append("discovery means absent from the available history; it does not prove the track was never heard")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": dict(categories)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["context", "feedback", "validate", "record", "delivery"])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--readback", type=Path)
    parser.add_argument("--pulse-json", type=Path, help="saved fetch_pulse capture, valid for one hour")
    parser.add_argument("--artist")
    parser.add_argument("--title", default="")
    parser.add_argument("--verdict", choices=["like", "dislike", "skip"])
    parser.add_argument("--note", default="")
    parser.add_argument("--playlist-id")
    parser.add_argument("--since", type=int, default=0)
    parser.add_argument("--allow-repeat", action="store_true", help="only use when repeats were explicitly requested")
    parser.add_argument("--apply", action="store_true", help="persist feedback or delivery; default is a dry run")
    args = parser.parse_args()
    if args.command == "delivery":
        if not args.playlist_id:
            raise ValueError("delivery requires --playlist-id")
        matches = [d for d in state()["delivered"] if d["playlist_id"] == args.playlist_id
                   and args.since <= d["at"] <= time.time() + 300]
        if not matches:
            return {"ok": False, "error": "no validated delivery was recorded for this job"}
        d = matches[-1]
        return {"ok": True, "data": {"playlist_id": d["playlist_id"], "at": d["at"],
                                     "count": len(d["tracks"]), "counts": d["counts"]}}
    if args.command == "feedback":
        if not args.artist or not args.verdict:
            raise ValueError("feedback requires --artist and --verdict; an empty --title covers the whole artist")
        event = {"at": int(time.time()), "artist": args.artist, "title": args.title,
                 "artist_key": artist_key(args.artist), "title_key": normalize_name(args.title),
                 "verdict": args.verdict, "note": args.note}
        if not args.apply:
            return {"ok": True, "dry_run": True, "event": event}
        with (ROOT / ".feedback.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = state()
            data["feedback"].append(event)
            atomic_json(ROOT / "feedback.json", data)
        return {"ok": True, "saved": event}
    pulse = json.loads(args.pulse_json.read_text()) if args.pulse_json else fetch_pulse()
    if args.command == "context":
        return context(pulse)
    if not args.manifest:
        raise ValueError("validate/record requires --manifest")
    manifest = json.loads(args.manifest.read_text())
    readback = json.loads(args.readback.read_text()) if args.readback else None
    if args.command == "record" and (not readback or not manifest.get("playlist_id")):
        raise ValueError("record requires playlist_id in the manifest and a --readback taken with get_playlist")
    with (ROOT / ".feedback.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = state()
        # Rechecking an already recorded playlist must not reject its own exposure.
        prior = {**data, "delivered": [d for d in data["delivered"]
                 if d["playlist_id"] != manifest.get("playlist_id")]}
        verdict = validate(manifest, pulse, prior, args.allow_repeat, readback)
        if not verdict["ok"] or args.command == "validate":
            return verdict
        if not args.apply:
            return {**verdict, "dry_run": True}
        previous = [d for d in data["delivered"] if d["playlist_id"] == manifest["playlist_id"]]
        if previous:
            def signature(tracks):
                return [(t["videoId"], track_key(t)) for t in tracks]
            if signature(previous[-1]["tracks"]) != signature(manifest["tracks"]):
                return {"ok": False, "error": "playlist already recorded with different content; previous record preserved"}
            return {**verdict, "already_recorded": True}
        data["delivered"].append({"at": int(time.time()), "playlist_id": manifest["playlist_id"],
                                  "tracks": manifest["tracks"], "counts": verdict["counts"]})
        atomic_json(ROOT / "feedback.json", data)
        return {**verdict, "recorded": manifest["playlist_id"]}


if __name__ == "__main__":
    try:
        result = main()
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)
