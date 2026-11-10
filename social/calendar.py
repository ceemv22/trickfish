"""Render social/queue.json as a phone-friendly Markdown calendar for manual posting.

    python social/calendar.py  ->  docs/social/calendar.md
"""
import datetime
import json
import pathlib
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL = ZoneInfo("Europe/Zagreb")


def main():
    entries = json.loads((ROOT / "social" / "queue.json").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in entries}
    lines = ["# Posting calendar", "",
             "Manual posting until the autoposter is switched on. Times are Croatian local time.",
             "For each entry: copy the text, attach the image if there is one, and post.",
             "**Reply** means: open the post named there and reply to it, so the answer threads under the question.",
             ""]
    day = None
    for entry in entries:
        when = datetime.datetime.fromisoformat(entry["scheduled_utc"].replace("Z", "+00:00")).astimezone(LOCAL)
        if entry["day"] != day:
            day = entry["day"]
            lines += ["---", "", "## Day %s · %s" % (day, when.strftime("%a %d %b")), ""]
        kind = "Reply to: *%s*" % by_id[entry["reply_to"]]["text"].splitlines()[0][:60] if entry.get("reply_to") else "New post"
        lines += ["### %s · %s · %s" % (when.strftime("%H:%M"), entry["slot"], kind), ""]
        if entry.get("poll"):
            options = " / ".join(entry["poll"]["options"])
            lines += ["Poll options: **%s** (%d hours)" % (options, entry["poll"]["duration_minutes"] // 60), ""]
        lines += ["```text", entry["text"], "```", ""]
        if entry.get("image"):
            lines += ["![image](../../%s)" % entry["image"], "", "Image: `%s`" % entry["image"], ""]
    out = ROOT / "docs" / "social" / "calendar.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", out, len(entries), "entries")


if __name__ == "__main__":
    main()
