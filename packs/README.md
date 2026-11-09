# Packs

Each pack lives in `packs/<name>/` with `traps.json` (finder output) and `notes.json` (title, method text, curated order and the per-trap explanations). Both are paid product content and are git-ignored, because this repository is public. Keep the owner's copy of these files outside the repository; the rendered PDF/PGN can always be regenerated from them:

```bash
PYTHONPATH=src python -m trickfish.trappack_render packs/<name>/traps.json --notes packs/<name>/notes.json --output dist/<name>
```

| Pack | Root | Side | Band | Games | Traps |
| --- | --- | --- | --- | --- | --- |
| e4e5-white-1200 | 1.e4 e5 | White | 1200-1599 | 902,003 | 23 of 38 found |
