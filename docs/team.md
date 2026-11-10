# Trickfish team

Claude runs Trickfish as CEO/CTO for the owner (@Ceemv22) and delegates specialist work to agents. Names are for tracking; each agent works from the files listed.

| Name | Role | Works from / produces |
| --- | --- | --- |
| Claude | CEO / CTO | Strategy, decisions, trap pipeline (`src/trickfish/trappack.py`, `lichess_db.py`), coordination |
| Iris | Design researcher | `docs/design/research.md` |
| Milo | Designer | `src/trickfish/studio/`, `docs/design/route-a.md`, all cards, store images and the PDF book |
| Vera | Art director (2000+ player) | `docs/design/review-1.md`, `review-2.md` |
| Theo | Copywriter | `docs/copy/research.md`, `voice.md`, `copy.md`, `pdf.md` |
| Nora | Editor | `docs/copy/edit-1.md` |
| Ivan | QA | `docs/design/pdf-qa.md` |
| Sam | Social media manager (runs on a cheaper model) | `docs/social/`, `social/queue.json`, `social/post.py` |

Cost rules: routine work runs on a cheaper model; content is produced in monthly batches; daily posting runs without AI (GitHub Actions + X API).
