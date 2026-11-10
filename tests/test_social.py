import datetime as dt
import json
import re
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "social"))
import post  # noqa: E402

QUEUE = json.loads((REPO / "social" / "queue.json").read_text(encoding="utf-8"))


def utc(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


class QueueSchema(unittest.TestCase):
    def test_required_fields_and_slots(self):
        for e in QUEUE:
            for k in ("id", "day", "slot", "scheduled_utc", "text"):
                self.assertIn(k, e, e.get("id"))
            self.assertIn(e["slot"], ("morning", "evening"))
            utc(e["scheduled_utc"])

    def test_ids_unique(self):
        ids = [e["id"] for e in QUEUE]
        self.assertEqual(len(ids), len(set(ids)))

    def test_times_strictly_increasing_and_start_day_2(self):
        times = [utc(e["scheduled_utc"]) for e in QUEUE]
        self.assertEqual(times, sorted(set(times)))
        self.assertEqual(times[0].date().isoformat(), "2026-11-11")

    def test_reply_to_references_earlier_entry(self):
        seen = set()
        for e in QUEUE:
            if e.get("reply_to"):
                self.assertIn(e["reply_to"], seen, e["id"])
            seen.add(e["id"])

    def test_text_length(self):
        for e in QUEUE:
            n = post.weighted_length(e["text"])
            self.assertLessEqual(n, 280, f"{e['id']} is {n}")

    def test_links_counted_as_23(self):
        self.assertEqual(post.weighted_length("https://example.com/a/very/long/path?x=1"), 23)
        self.assertEqual(post.weighted_length("hi https://example.com/x"), 3 + 23)

    def test_links_only_where_planned(self):
        for e in QUEUE:
            if "http" in e["text"]:
                self.assertTrue(e["slot"] == "evening" or e["day"] in (20, 28), e["id"])
        reminders = [e for e in QUEUE if e["day"] >= 15 and "http" in e["text"]]
        self.assertLessEqual(len(reminders), 2)

    def test_images_exist_and_not_with_polls(self):
        for e in QUEUE:
            if e.get("image"):
                self.assertTrue((REPO / e["image"]).is_file(), e["image"])
                self.assertNotIn("poll", e)

    def test_polls_valid(self):
        for e in QUEUE:
            if "poll" in e:
                opts = e["poll"]["options"]
                self.assertTrue(2 <= len(opts) <= 4)
                self.assertTrue(all(0 < len(o) <= 25 for o in opts), opts)
                self.assertTrue(5 <= e["poll"]["duration_minutes"] <= 10080)

    def test_no_forbidden_style(self):
        for e in QUEUE:
            self.assertNotIn("—", e["text"], e["id"])
            self.assertIsNone(re.search(r"(^|\s)#\w", e["text"]), e["id"])


class FakeClient:
    def __init__(self, fail_on=None):
        self.sent = []
        self.uploads = []
        self.fail_on = fail_on

    def upload_media(self, path):
        self.uploads.append(str(path))
        return "m%d" % len(self.uploads)

    def create_tweet(self, payload):
        if self.fail_on is not None and len(self.sent) == self.fail_on:
            raise RuntimeError("boom")
        self.sent.append(payload)
        return "t%d" % len(self.sent)


MINI = [
    {"id": "a", "day": 2, "slot": "morning", "scheduled_utc": "2026-11-11T13:00:00Z",
     "text": "one", "image": "social/images/trap-19.png"},
    {"id": "b", "day": 2, "slot": "evening", "scheduled_utc": "2026-11-11T19:00:00Z",
     "text": "two", "reply_to": "a"},
    {"id": "c", "day": 3, "slot": "morning", "scheduled_utc": "2026-11-12T13:00:00Z",
     "text": "three", "poll": {"options": ["x", "y"], "duration_minutes": 300}},
]


class Poster(unittest.TestCase):
    def go(self, now, state=None, client=None, **kw):
        state = state if state is not None else {"posted": {}}
        client = client or FakeClient()
        kw.setdefault("max_late_hours", 200)
        n = post.run(MINI, state, utc(now), client, dry_run=kw.pop("dry_run", False), **kw)
        return n, state, client

    def test_nothing_due_before_first_time(self):
        n, state, client = self.go("2026-11-11T12:59:00Z")
        self.assertEqual((n, client.sent), (0, []))

    def test_posts_due_in_order_with_threading_and_media(self):
        n, state, client = self.go("2026-11-11T19:05:00Z")
        self.assertEqual(n, 2)
        self.assertEqual(state["posted"], {"a": "t1", "b": "t2"})
        self.assertEqual(client.sent[0]["media"], {"media_ids": ["m1"]})
        self.assertEqual(client.sent[1]["reply"], {"in_reply_to_tweet_id": "t1"})
        self.assertNotIn("inflight", state)

    def test_poll_payload(self):
        state = {"posted": {"a": "t1", "b": "t2"}}
        n, state, client = self.go("2026-11-12T13:10:00Z", state)
        self.assertEqual(client.sent[0]["poll"], {"options": ["x", "y"], "duration_minutes": 300})

    def test_idempotent(self):
        n, state, client = self.go("2026-11-11T19:05:00Z")
        n2, _, client2 = self.go("2026-11-11T19:35:00Z", state)
        self.assertEqual((n2, client2.sent), (0, []))

    def test_cap(self):
        n, state, client = self.go("2026-11-12T13:10:00Z", max_posts=1)
        self.assertEqual((n, list(state["posted"])), (1, ["a"]))

    def test_stops_on_first_error_and_keeps_earlier_posts(self):
        client = FakeClient(fail_on=1)
        state = {"posted": {}}
        with self.assertRaises(RuntimeError):
            post.run(MINI, state, utc("2026-11-12T13:10:00Z"), client, dry_run=False, max_late_hours=200)
        self.assertEqual(state["posted"], {"a": "t1"})
        self.assertEqual(state["inflight"], "b")
        with self.assertRaises(RuntimeError):  # refuses to run until resolved
            post.run(MINI, state, utc("2026-11-12T13:10:00Z"), FakeClient(), dry_run=False)

    def test_dry_run_posts_nothing_and_leaves_state(self):
        n, state, client = self.go("2026-11-11T19:05:00Z", dry_run=True, client=None)
        self.assertEqual((n, state["posted"]), (2, {}))

    def test_stale_entries_are_skipped(self):
        n, state, client = self.go("2026-11-14T13:00:00Z", max_late_hours=24)
        self.assertEqual((n, client.sent), (0, []))

    def test_reply_skipped_when_parent_missing(self):
        queue = [MINI[1]]
        client = FakeClient()
        n = post.run(queue, {"posted": {}}, utc("2026-11-11T19:05:00Z"), client, dry_run=False)
        self.assertEqual((n, client.sent), (0, []))

    def test_state_file_written_per_post(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "state.json"
            post.run(MINI, {"posted": {}}, utc("2026-11-11T19:05:00Z"), FakeClient(), False, 3, 24, p)
            self.assertEqual(json.loads(p.read_text())["posted"], {"a": "t1", "b": "t2"})

    def test_mark_posted_and_skipped_cli(self):
        with tempfile.TemporaryDirectory() as d:
            q = pathlib.Path(d) / "q.json"
            q.write_text(json.dumps(MINI))
            st = pathlib.Path(d) / "s.json"
            base = ["--queue", str(q), "--state", str(st)]
            self.assertEqual(post.main(base + ["--mark-posted", "a", "--tweet-id", "999"]), 0)
            self.assertEqual(post.main(base + ["--mark-skipped", "c"]), 0)
            self.assertEqual(post.main(base + ["--mark-posted", "zzz", "--tweet-id", "1"]), 1)
            self.assertEqual(post.main(base + ["--mark-posted", "b"]), 1)
            state = json.loads(st.read_text())
            client = FakeClient()
            post.run(MINI, state, utc("2026-11-12T13:10:00Z"), client, False, max_late_hours=200)
            self.assertEqual(client.sent, [{"text": "two", "reply": {"in_reply_to_tweet_id": "999"}}])
            self.assertNotIn("c", state["posted"])

    def test_main_dry_runs_without_credentials(self):
        import os
        saved = {k: os.environ.pop(k, None) for k in post.CRED_VARS}
        try:
            with tempfile.TemporaryDirectory() as d:
                st = pathlib.Path(d) / "s.json"
                rc = post.main(["--now", "2030-01-01T00:00:00Z", "--state", str(st)])
                self.assertEqual(rc, 0)
                self.assertFalse(st.exists())
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
