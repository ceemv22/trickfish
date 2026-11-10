#!/usr/bin/env python3
"""Zero-AI poster for @trickfishchess.

Reads social/queue.json, posts every due entry that is not yet in
social/state.json, in order, and records the resulting tweet ids.

Dry-run is the default whenever credentials are missing (or --dry-run is given).
Credentials come from X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
QUEUE = HERE / "queue.json"
STATE = HERE / "state.json"

TWEET_URL = "https://api.x.com/2/tweets"
MEDIA_URL = os.environ.get("X_MEDIA_UPLOAD_URL", "https://upload.twitter.com/1.1/media/upload.json")
CRED_VARS = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
URL_RE = re.compile(r"https?://\S+")
URL_WEIGHT = 23
MAX_WEIGHT = 280
# Entries more than this many hours overdue are skipped, not posted late.
DEFAULT_MAX_LATE_HOURS = 24


def log(msg):
    print(f"[social] {msg}", flush=True)


def char_weight(ch):
    cp = ord(ch)
    if cp <= 4351 or 8192 <= cp <= 8205 or 8208 <= cp <= 8223 or 8242 <= cp <= 8247:
        return 1
    return 2


def weighted_length(text):
    """Approximation of X's weighting: URLs count 23, most Latin text 1, CJK/emoji 2."""
    total = 0
    pos = 0
    for m in URL_RE.finditer(text):
        total += sum(char_weight(c) for c in text[pos:m.start()]) + URL_WEIGHT
        pos = m.end()
    return total + sum(char_weight(c) for c in text[pos:])


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path, state):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


class XClient:
    """Thin OAuth 1.0a user-context client. Replaced by a fake in tests."""

    def __init__(self, key, secret, token, token_secret):
        from requests_oauthlib import OAuth1Session
        self.session = OAuth1Session(key, client_secret=secret,
                                     resource_owner_key=token,
                                     resource_owner_secret=token_secret)

    def upload_media(self, path):
        with open(path, "rb") as fh:
            r = self.session.post(MEDIA_URL, files={"media": fh}, timeout=60)
        if r.status_code >= 300:
            raise RuntimeError(f"media upload failed: {r.status_code} {r.text[:300]}")
        data = r.json()
        return str(data.get("media_id_string") or data["media_id"])

    def create_tweet(self, payload):
        r = self.session.post(TWEET_URL, json=payload, timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"tweet failed: {r.status_code} {r.text[:300]}")
        return str(r.json()["data"]["id"])


def build_payload(entry, state, upload):
    payload = {"text": entry["text"]}
    if entry.get("reply_to"):
        parent = state["posted"].get(entry["reply_to"])
        if not parent:
            raise RuntimeError(f"{entry['id']}: parent {entry['reply_to']} is not posted")
        payload["reply"] = {"in_reply_to_tweet_id": parent}
    if entry.get("poll"):
        payload["poll"] = {"options": list(entry["poll"]["options"]),
                           "duration_minutes": int(entry["poll"]["duration_minutes"])}
    if entry.get("image"):
        payload["media"] = {"media_ids": [upload(REPO / entry["image"])]}
    return payload


def run(queue, state, now, client=None, dry_run=True, max_posts=3,
        max_late_hours=DEFAULT_MAX_LATE_HOURS, state_path=None):
    """Post due entries. Returns the number posted (or that would be posted).

    Stops at the first error (raises). State is saved after every post.
    """
    state.setdefault("posted", {})
    if state.get("inflight") and not dry_run:
        raise RuntimeError(
            f"entry {state['inflight']} may have been sent without a recorded result. "
            "Check @trickfishchess, then fix social/state.json (add it to 'posted' or "
            "remove 'inflight') before running again.")
    count = 0
    virtual = set()  # dry run: entries that would have been posted
    for entry in queue:
        if entry["id"] in state["posted"]:
            continue
        due = parse_time(entry["scheduled_utc"])
        if due > now:
            break  # queue is time-ordered, nothing later is due
        late = (now - due).total_seconds() / 3600
        if late > max_late_hours:
            log(f"skip {entry['id']}: {late:.0f}h overdue (limit {max_late_hours}h)")
            continue
        parent = entry.get("reply_to")
        if parent and parent not in state["posted"] and parent not in virtual:
            log(f"skip {entry['id']}: parent {parent} was not posted")
            continue
        if count >= max_posts:
            log(f"cap of {max_posts} posts reached, stopping")
            break
        if weighted_length(entry["text"]) > MAX_WEIGHT:
            raise RuntimeError(f"{entry['id']} is over {MAX_WEIGHT} weighted characters")
        if dry_run:
            log(f"DRY RUN would post {entry['id']} (day {entry['day']} {entry['slot']})"
                f"{' [poll]' if entry.get('poll') else ''}{' [image]' if entry.get('image') else ''}")
            virtual.add(entry["id"])
            count += 1
            continue
        payload = build_payload(entry, state, client.upload_media)
        state["inflight"] = entry["id"]
        if state_path:
            save_state(state_path, state)
        tweet_id = client.create_tweet(payload)
        state["posted"][entry["id"]] = tweet_id
        state.pop("inflight", None)
        if state_path:
            save_state(state_path, state)
        log(f"posted {entry['id']} -> tweet {tweet_id}")
        count += 1
    log(f"{'would post' if dry_run else 'posted'} {count} entr{'y' if count == 1 else 'ies'}")
    return count


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="never call the API (default without credentials)")
    ap.add_argument("--max-posts", type=int, default=3, help="cap per run (default 3)")
    ap.add_argument("--max-late-hours", type=float, default=DEFAULT_MAX_LATE_HOURS)
    ap.add_argument("--now", help="override the clock (ISO UTC), for testing")
    ap.add_argument("--queue", default=str(QUEUE))
    ap.add_argument("--state", default=str(STATE))
    args = ap.parse_args(argv)

    queue = load_json(pathlib.Path(args.queue), [])
    state_path = pathlib.Path(args.state)
    state = load_json(state_path, {"posted": {}})
    now = parse_time(args.now) if args.now else dt.datetime.now(dt.timezone.utc)

    creds = [os.environ.get(v, "").strip() for v in CRED_VARS]
    dry = args.dry_run or not all(creds)
    if dry and not args.dry_run:
        log("credentials missing: dry run")
    client = None if dry else XClient(*creds)
    try:
        run(queue, state, now, client, dry, args.max_posts, args.max_late_hours,
            None if dry else state_path)
    except Exception as exc:  # stop on first error, loudly
        log(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
