"""Build docs/social/daily-pack.md: one phone-friendly page for scheduling Days 2-14.

    python social/daily_pack.py

Reads social/queue.json (X posts) and docs/social/video-captions.md (TikTok /
YouTube Shorts text). Re-runnable; overwrites the output.
"""
import json
import re
import sys
from pathlib import Path

# social/calendar.py would shadow the stdlib module, so keep this folder off sys.path.
sys.path = [p for p in sys.path if Path(p or ".").resolve() != Path(__file__).resolve().parent]
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://github.com/ceemv22/trickfish/raw/claude/gracious-ritchie-pnenn3/"
TRAPS = {2: 19, 3: 17, 4: 12, 5: 22, 6: 16, 7: 3, 8: 7, 9: 13, 10: 20, 11: 8, 12: 23, 13: 6, 14: 14}
HEADER = """# Trickfish daily pack, Days 2-14

1. Open this each evening and work through tomorrow's day, top to bottom. Tap a text box to copy it.
2. X scheduling only works on desktop x.com (Compose > calendar icon). Schedule the question for 14:00 Croatian time, with its image.
3. YouTube Shorts and TikTok: upload the mp4 from the video link, paste the text, schedule for 14:00. Shorts also takes the thumbnail.
4. TikTok: switch on "Content disclosure: Your brand" before you schedule.
5. Replies can't be scheduled. Post each evening reply by hand after work, as a reply to that day's question.
"""


def block(text):
    return "```text\n%s\n```\n" % text.strip()


def links(path):
    return "`%s`\n\n%s%s\n" % (path, RAW, path)


def captions():
    """{trap number: {'tiktok','title','desc'}} parsed from video-captions.md."""
    md = (ROOT / "docs/social/video-captions.md").read_text(encoding="utf-8")
    out = {}
    for sec in re.split(r"\n---\n", md):
        m = re.search(r"## trap-(\d+)\.mp4", sec)
        if not m:
            continue
        def get(label):
            r = re.search(r"\*\*%s\*\*[^\n]*\n```text\n(.*?)\n```" % re.escape(label), sec, re.S)
            return r.group(1).strip()
        out[int(m.group(1))] = {"tiktok": get("TikTok"), "title": get("YouTube Shorts title"),
                                "desc": get("YouTube Shorts description")}
    return out


def main():
    queue = {q["id"]: q for q in json.loads((ROOT / "social/queue.json").read_text(encoding="utf-8"))}
    caps = captions()
    parts = [HEADER]
    for day, trap in TRAPS.items():
        m, e = queue["d%02d-m" % day], queue["d%02d-e" % day]
        assert m["image"] == "social/images/trap-%02d.png" % trap, (day, m["image"])
        assert e["image"] == "social/images/trap-%02d-answer.png" % trap, (day, e["image"])
        when = datetime.strptime(m["scheduled_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Zagreb"))
        assert when.hour == 14, when
        video, thumb = "social/video/trap-%02d.mp4" % trap, "social/video/thumbs/trap-%02d-thumb.png" % trap
        for f in (video, thumb, m["image"], e["image"]):
            assert (ROOT / f).exists(), f
        c = caps[trap]
        parts.append("\n---\n\n## Day %d · %s · Trap %d\n" % (day, when.strftime("%a %d %b %Y"), trap))
        parts.append("\n### X question (14:00)\n\n" + block(m["text"]) + "\nImage: " + links(m["image"]))
        parts.append("\n### YouTube Shorts (14:00)\n\nVideo: " + links(video) + "\nThumbnail: " + links(thumb) +
                     "\nTitle:\n\n" + block(c["title"]) + "\nDescription:\n\n" + block(c["desc"]))
        parts.append("\n### TikTok (14:00)\n\nVideo: " + links(video) +
                     "\nReminder: Content disclosure: Your brand\n\nCaption:\n\n" + block(c["tiktok"]))
        parts.append("\n### X evening reply (post by hand after work)\n\n" + block(e["text"]) +
                     "\nImage: " + links(e["image"]))
    out = ROOT / "docs/social/daily-pack.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
