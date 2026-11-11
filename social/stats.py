"""Snapshot Trickfish numbers into social/stats.csv (one row per product per run).

Gumroad: product sales counts and revenue via the Gumroad API. The access token
is injected by the session's network proxy for api.gumroad.com, or read from
GUMROAD_TOKEN when run elsewhere. YouTube: public channel and video statistics
via the YouTube Data API when YOUTUBE_API_KEY (or a proxy-injected key) and
YOUTUBE_CHANNEL_HANDLE are available; skipped otherwise.

    python social/stats.py            # append a snapshot and print a summary
    python social/stats.py --dry-run  # print only
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "social" / "stats.csv"
FIELDS = ["taken_utc", "source", "item", "metric", "value"]


def get_json(url, headers=None):
    request = urllib.request.Request(url, headers={"User-Agent": "trickfish-stats", **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def gumroad():
    token = os.environ.get("GUMROAD_TOKEN")
    headers = {"Authorization": "Bearer " + token} if token else {}
    data = get_json("https://api.gumroad.com/v2/products", headers)
    if not data.get("success"):
        raise RuntimeError("Gumroad API refused the request")
    rows = []
    for product in data.get("products", []):
        name = product.get("name", "?")
        rows.append(("gumroad", name, "sales", product.get("sales_count") or 0))
        rows.append(("gumroad", name, "revenue_usd", round((product.get("sales_usd_cents") or 0) / 100, 2)))
    return rows


def youtube():
    handle = os.environ.get("YOUTUBE_CHANNEL_HANDLE", "trickfishchess")
    key = os.environ.get("YOUTUBE_API_KEY")
    suffix = ("&key=" + urllib.parse.quote(key)) if key else ""
    base = "https://www.googleapis.com/youtube/v3/"
    channel = get_json(base + "channels?part=statistics,contentDetails&forHandle=" + handle + suffix)
    if not channel.get("items"):
        return []
    item = channel["items"][0]
    stats = item["statistics"]
    rows = [("youtube", "@" + handle, "subscribers", int(stats.get("subscriberCount", 0))),
            ("youtube", "@" + handle, "views", int(stats.get("viewCount", 0))),
            ("youtube", "@" + handle, "videos", int(stats.get("videoCount", 0)))]
    uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
    listing = get_json(base + "playlistItems?part=contentDetails&maxResults=50&playlistId=" + uploads + suffix)
    ids = [entry["contentDetails"]["videoId"] for entry in listing.get("items", [])]
    if ids:
        videos = get_json(base + "videos?part=snippet,statistics&id=" + ",".join(ids) + suffix)
        for video in videos.get("items", []):
            title = video["snippet"]["title"][:60]
            for metric in ("viewCount", "likeCount", "commentCount"):
                rows.append(("youtube", title, metric, int(video["statistics"].get(metric, 0))))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    taken = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    rows, problems = [], []
    for name, source in (("gumroad", gumroad), ("youtube", youtube)):
        try:
            rows += source()
        except Exception as error:  # one source failing must not hide the others
            problems.append("%s: %s" % (name, error))
    for source, item, metric, value in rows:
        print("%-8s %-60s %-12s %s" % (source, item, metric, value))
    for problem in problems:
        print("SKIPPED", problem)
    if rows and not args.dry_run:
        new = not CSV.exists()
        with CSV.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if new:
                writer.writerow(FIELDS)
            for source, item, metric, value in rows:
                writer.writerow([taken, source, item, metric, value])
        print("appended %d rows to %s" % (len(rows), CSV))


if __name__ == "__main__":
    main()
