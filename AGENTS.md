# AGENTS.md

## Checks

```bash
pip install -r requirements.txt
python -m unittest discover tests
```

The unit tests need Inter Tight installed (`assets/InterTight.ttf`); without it cairo falls back to another face and the covers come out wrong without failing. Full check needs Docker: build the image, run it with `COVER_TOKEN`, then `SERVICE_URL=http://127.0.0.1:8000 COVER_TOKEN=<token> python tests/service_check.py`. The Build workflow does both and publishes the image to GHCR on `main`; servers only pull it.

## Review rules

- Output carries no metadata: PNG keeps only `IHDR`, `PLTE`, `tRNS`, `IDAT`, `IEND`; WebP has no EXIF, ICC or XMP.
- The geometry matches the `portada-1200x630` template in brand-kit's `src/kit.py`. If the template changes there, change it here too.
- `assets/criptonautas-horizontal-color.svg` is a copy of brand-kit's `dist/logo/horizontal/`. Replace it from there, never edit it.
- `wrap_title` measures with Pillow at weight 800 without the -1.1 letter-spacing, so it overestimates and cairo always fits. If the tracking or weight changes, measure again.
- The server never decodes images from outside: the illustration is command-line only. Keep the token check, the 4 KB body limit and the 10 s timeout.
- Everything in English: names, endpoints, headers, comments, messages. Descriptive names, no abbreviations nobody would guess.
- Comments explain why, in one plain line. No history, no tool tags.
- Docker file is `docker-compose.yml`, and it holds a service block meant to be pasted into the n8n `docker-compose.yml`. It uses the published image, never `build:`.
- Commits use Discourse prefixes: `FEATURE:`, `FIX:`, `DEV:`, `DOCS:`.
