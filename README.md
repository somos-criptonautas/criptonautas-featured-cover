# criptonautas-featured-cover

**ENGLISH** | [ESPAÑOL](README.es.md)

Maintained by Criptonautas. Not affiliated with or endorsed by the Ghost Foundation or Civilized Discourse Construction Kit, Inc.

Draws a 1200×630 cover for Ghost posts without a featured image and for Discourse wiki, course and glossary topics: a label and the title on the Criptonautas template from [brand-kit](https://github.com/somos-criptonautas/brand-kit). The title is set in Inter Tight, up to 3 lines, wrapped automatically. Output is PNG or WebP with no metadata.

It is a small internal HTTP service. n8n calls it; it is never exposed to the internet.

## How it fits

1. Ghost fires the `post.published` webhook to n8n.
2. The n8n workflow `ghost-cover-add` reads the post. If it has no featured image, it asks this service for a cover, uploads it to Ghost and sets it as the featured image.
3. Discourse fires its topic webhook to n8n. The workflow `discourse-community-cover-add` takes topics tagged `wiki` or in the Curso and Glosario categories whose first post has no image, asks for a cover in the `community` style and adds it at the end of the first post, which makes it the topic thumbnail.

## Install

GitHub Actions tests the image and publishes it to `ghcr.io/somos-criptonautas/criptonautas-featured-cover` on every push to `main`. Nothing is built on the server.

Next to the `docker-compose.yml` that runs n8n, create the token file:

```bash
umask 077; printf 'COVER_TOKEN=%s\n' "$(openssl rand -hex 32)" > cover.env
```

Paste the service from this repo's [`docker-compose.yml`](docker-compose.yml) under `services:` in that `docker-compose.yml`. If the n8n service lists `networks:`, add the same networks to this service. Then:

```bash
docker compose up -d criptonautas-featured-cover
docker compose ps criptonautas-featured-cover   # should say "healthy"
```

In n8n, an **HTTP Request** node:

- Method `POST`, URL `http://criptonautas-featured-cover:8000/cover`
- Authentication: Header Auth, name `Authorization`, value `Bearer <COVER_TOKEN>`
- Body JSON: `{"category": "...", "title": "...", "format": "webp"}`
- Response format: **File**. The next node gets the cover as binary data.

## Update

Push to `main`, wait for the Build workflow to pass, then on the server:

```bash
docker compose pull criptonautas-featured-cover
docker compose up -d criptonautas-featured-cover
```

## API

- `POST /cover` with `Authorization: Bearer <COVER_TOKEN>` and JSON `{"category", "title", "format"}` → the image.
  - `format` is `png` (default) or `webp`.
  - `style` is `article` (default: diagonal hatching and the horizontal logo) or `community` (a grid and the "Criptonautas comunidad" sub-logo).
  - Category up to 30 characters, title up to 140 and 3 lines.
  - `Content-Disposition` carries `cover.<format>`, so Ghost accepts the upload.
  - Errors: `401` wrong token, `400` no `Content-Length`, `413` body over 4 KB, `422` with the reason as text (title too long, invalid JSON, an `image` field).
- `GET /health` → `ok`.

The illustration slot takes an image only from the command line:

```bash
python cover.py --category "Course" --title "What is a wallet" --image art.png
# → covers/what-is-a-wallet-cover.png and .webp
```

## Production settings

The service refuses to start without a `COVER_TOKEN` of 32 or more characters. The service block runs read-only, as an unprivileged user, with no Linux capabilities, no published ports, and limits of 256 MB memory, half a CPU and 64 processes. It logs no titles or client addresses.

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover tests                                                   # needs Inter Tight installed (assets/)
SERVICE_URL=http://127.0.0.1:8000 COVER_TOKEN=<token> python tests/service_check.py  # against a running container
```

GitHub Actions runs the unit tests, builds the image, checks the running container with the production limits, and publishes it only if everything passes.

## Credits and license

Font: [Inter Tight](https://github.com/googlefonts/inter-tight) by Rasmus Andersson (SIL Open Font License, [`assets/OFL-inter-tight.txt`](assets/OFL-inter-tight.txt)). Logo: from [brand-kit](https://github.com/somos-criptonautas/brand-kit).

Code: [MIT](LICENSE). README text: [CC BY-NC-SA 4.0](CC-BY-NC-SA-4.0.txt).
