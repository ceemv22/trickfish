# Metricool scheduling

Since 2026-11-15, YouTube Shorts and TikTok are scheduled by Claude through the Metricool connector (brand id 8133957, timezone Europe/Warsaw). Videos are sent as public raw GitHub URLs (`https://raw.githubusercontent.com/ceemv22/trickfish/claude/gracious-ritchie-pnenn3/social/video/trap-NN.mp4`) and Metricool copies them to its own storage when the post is created.

Per post:
- YouTube: one post per day at 14:00 local, `youtubeData.type = short`, title and description from `docs/social/video-captions.md`, `madeForKids = false`, category EDUCATION.
- TikTok: one post per day at 14:00, caption from `video-captions.md`, `tiktokData.title` required (we use the YouTube title), `commercialContentOwnBrand = true` (our own product).
- No custom thumbnails (Metricool only applies them to verified YouTube channels and TikTok business accounts) and no added music (not available through the API).

X is not connected to Metricool; the owner schedules X questions on x.com and posts the evening replies by hand.

Scheduled so far: Days 7–13 (16–22 Nov 2026), traps 3, 7, 13, 20, 8, 23, 6, on both networks.

## X through Typefully

Since 2026-11-15, X is scheduled by Claude through the Typefully connector (social set 365434, @trickfishchess). Images are uploaded with `create_media_upload` and a plain `curl -T` PUT of `social/images/trap-NN.png` / `trap-NN-answer.png` to the presigned URL. Each day: the question from `social/queue.json` at 14:00 with the question card, and the answer at 20:00 as a standalone post starting "Answer:" with the answer card (a reply needs the question's URL, which only exists after it is published). Answers must stay within 280 weighted characters (links count 23).

Scheduled so far on X: Days 7–13 (16–22 Nov 2026), questions at 14:00 and answers at 20:00.
