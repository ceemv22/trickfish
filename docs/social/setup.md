# Setup: turning on the poster

You do this once, about 20 minutes. Until you do, the poster only does dry runs and posts nothing.

## 1. Create the X developer app

1. Sign in to https://developer.x.com with the @trickfishchess account (or the account that owns it) and create a developer project and app.
2. Open the app's **User authentication settings** and set **App permissions** to **Read and Write**. Do this before generating tokens: tokens made earlier with Read-only stay Read-only.
3. Under **Keys and tokens**, copy:
   - API Key and API Key Secret (the "consumer" keys)
   - Access Token and Access Token Secret, generated for @trickfishchess. The page should say they were created with Read and Write permissions. If it says Read only, regenerate them after step 2.
4. This uses OAuth 1.0a with user tokens. You don't need OAuth 2.0 or a bearer token.

## 2. Add credit

X now charges per use. In the Developer Console, open **Billing** and add credit (a small top-up is enough to start). When the credit runs out, posts fail and the poster stops. Nothing is lost, the queue just waits.

Cost, as of when this was written (check the Developer Console, prices change): about USD 0.015 per post, but about USD 0.20 for a post that contains a link. That is why Days 15–30 only have two link posts (Days 20 and 28), while Days 2–14 have 13 link posts in the answer replies. Roughly: Days 2–14 cost about USD 2.9, Days 15–30 about USD 0.7. I could not confirm these figures against X's own page from where I work, so treat them as an estimate.

## 3. Add the four GitHub secrets

In the GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**. Create four secrets with exactly these names:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_SECRET`

Never paste these into a file, issue or chat.

## 4. Merge to the default branch

GitHub only runs scheduled workflows from the default branch (`main`). The workflow file, `social/` and the images must be merged to `main`, or nothing will fire. If the branch is merged late, entries more than 24 hours overdue are skipped rather than posted late, so merge before 11 Nov 2026 13:00 UTC or Day 2 is lost.

Also check **Settings → Actions → General → Workflow permissions**. The workflow asks for write access itself, but an organisation policy can override it. If state commits fail with a permissions error, set it to "Read and write".

## 5. Test it by hand

1. **Actions → social-poster → Run workflow**. Tick **Dry run** first. The log should list what would be posted and say nothing was sent.
2. A real test post: before Day 2 there is nothing due, so nothing posts. For a live test, temporarily set one entry's `scheduled_utc` to a past time (within 24 hours), run the workflow without dry run, check the tweet, then delete the test tweet by hand and put the state and queue back. Or just wait for Day 2.
3. Run once on demand any time: **Actions → social-poster → Run workflow**. It posts whatever is due, at most 3 per run.

If the secrets are missing, the workflow does a dry run and ends green. That is deliberate.

## 6. Pause and resume

- Pause: **Actions → social-poster → ⋯ → Disable workflow**. Re-enable the same way. Missed entries more than 24 hours late are skipped, not posted in a burst, so resuming after a long break skips what you missed.
- Skip one post: delete its entry from `social/queue.json` (do not delete ones that others reply to), or add its id to `social/state.json` under `posted` with any text value other than a real tweet id. A reply to a skipped post would fail, so skip both.

## What the poster does and doesn't do

- Posts text, images (resized to 1080x1350), polls and replies, with no AI involved. The posted tweet ids are saved in `social/state.json`, which the workflow commits back.
- Posts at most 3 per run and stops at the first error. If a post fails after being sent with no answer back (a timeout), it marks the entry as "inflight" and refuses to run again. Check the @trickfishchess timeline, then edit `social/state.json`: if the tweet is there, add `"<id>": "<tweet id>"` to `posted`, and remove `inflight` either way. The workflow log says which entry.
- Doesn't add alt text to images (the media metadata call is not wired in), doesn't read replies, and doesn't repair the queue.

## Things I could not verify

- **Media upload endpoint.** The poster uses the older v1.1 upload (`upload.twitter.com/1.1/media/upload.json`) with OAuth 1.0a. Sources I found disagree on whether X has retired it in favour of a v2 media endpoint. If the first image post fails with a media error, the log shows the response. Set `X_MEDIA_UPLOAD_URL` to the new URL in the workflow's `env`, and if the response shape differs, `upload_media` in `social/post.py` is one small function to change.
- **Pricing and credits.** See above. Look at the Developer Console, not at me.
- **Polls.** The poll fields follow X's v2 docs (2–4 options, up to 25 characters each, duration in minutes). I have not posted one for real. If polls are rejected, Days 16, 21 and 25 will stop the queue at that entry.
- **GitHub schedule delays.** Scheduled workflows can start late by several minutes under load, and GitHub disables schedules in a repo with no activity for 60 days. The state commits count as activity.
