#!/usr/bin/env python3
"""Draws the 1200x630 Criptonautas cover: category, title and an optional illustration on the brand-kit template.

    python cover.py --category Course --title "What is a wallet" [--image art.png] [--slug wallet] [--output covers]

Writes <slug>-cover.png and <slug>-cover.webp with no metadata.
Needs Inter Tight installed for cairo (the Dockerfile does it); otherwise cairo silently uses another face.
"""
import argparse
import base64
import html
import io
import re
import sys
import unicodedata
from pathlib import Path

import cairosvg
from PIL import Image, ImageFont

ASSETS = Path(__file__).resolve().parent / "assets"
TITLE_FONT = ASSETS / "InterTight.ttf"
LOCKUP = ASSETS / "criptonautas-horizontal-color.svg"

# Same geometry as the portada-1200x630 template in brand-kit's kit.py.
WIDTH, HEIGHT, SLOT_X = 1200, 630, 760
INK, PAPER, HALFTONE, VIOLET = "#14110F", "#E8E6E1", "#7E7973", "#5814EA"
TITLE_X, TITLE_Y0, TITLE_STEP, TITLE_SIZE, MAX_LINES = 64, 196, 66, 56, 3
# Pillow measures without the negative letter-spacing, so it overestimates: what fits here fits in cairo.
TITLE_MAX_WIDTH = SLOT_X - TITLE_X - 64
MAX_TITLE, MAX_CATEGORY, MAX_IMAGE_BYTES = 140, 30, 10 * 1024 * 1024
STYLES = ("article", "community")
# Bounding box of the wordmark path inside the lockup viewBox (x, y, width, height).
WORDMARK_BOX = (1703, 425, 6096, 850)
PNG_KEEP = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}


class InvalidCoverInput(ValueError):
    """Rejected input; the message goes back to the caller as is."""


def load_title_font():
    font = ImageFont.truetype(str(TITLE_FONT), TITLE_SIZE)
    font.set_variation_by_axes([800])
    return font


def wrap_title(title, font=None):
    """Splits the title into lines that fit the width; fails if it needs more than MAX_LINES."""
    font = font or load_title_font()
    lines = []
    for word in title.split():
        candidate = f"{lines[-1]} {word}" if lines else word
        if lines and font.getlength(candidate) <= TITLE_MAX_WIDTH:
            lines[-1] = candidate
        elif font.getlength(word) > TITLE_MAX_WIDTH:
            raise InvalidCoverInput(f'the word "{word}" does not fit on one line')
        else:
            lines.append(word)
    if len(lines) > MAX_LINES:
        raise InvalidCoverInput(f"the title takes {len(lines)} lines; the maximum is {MAX_LINES}. Shorten it.")
    return lines


def svg_inner(svg):
    view_box = re.search(r'viewBox="([^"]+)"', svg).group(1)
    body = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg.strip())
    return view_box, re.sub(r"<title>.*?</title>", "", body)


def load_illustration(data):
    """Reopens the image and re-encodes it as PNG: checks the format and drops its metadata."""
    if len(data) > MAX_IMAGE_BYTES:
        raise InvalidCoverInput("the illustration is over 10 MB")
    try:
        image = Image.open(io.BytesIO(data))
        if image.format not in ("PNG", "JPEG", "WEBP"):
            raise InvalidCoverInput("the illustration must be PNG, JPEG or WebP")
        image = image.convert("RGB")
    except InvalidCoverInput:
        raise
    except Exception:
        raise InvalidCoverInput("the illustration is not a valid image")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def build_cover_svg(category, title, image=None, style="article"):
    if style not in STYLES:
        raise InvalidCoverInput("style must be article or community")
    category, title = " ".join(category.split()), " ".join(title.split())
    if not title or not category:
        raise InvalidCoverInput("category and title are required")
    if len(title) > MAX_TITLE or len(category) > MAX_CATEGORY:
        raise InvalidCoverInput(f"at most {MAX_CATEGORY} characters of category and {MAX_TITLE} of title")
    tspans = "".join(f'<tspan x="{TITLE_X}" y="{TITLE_Y0 + i * TITLE_STEP}">{html.escape(line)}</tspan>'
                     for i, line in enumerate(wrap_title(title)))
    if image:
        slot = (f'<image x="{SLOT_X}" y="0" width="{WIDTH - SLOT_X}" height="{HEIGHT}" preserveAspectRatio="xMidYMid slice" '
                f'href="data:image/png;base64,{load_illustration(image)}"/>')
    elif style == "community":  # a grid instead of the diagonal hatching tells forum pages from articles
        lines = [f'<line x1="{x}" y1="0" x2="{x}" y2="{HEIGHT}"/>' for x in range(SLOT_X, WIDTH, 24)]
        lines += [f'<line x1="{SLOT_X}" y1="{y}" x2="{WIDTH}" y2="{y}"/>' for y in range(0, HEIGHT, 24)]
        slot = f'<g stroke="{HALFTONE}" stroke-width="1.2">{"".join(lines)}</g>'
    else:  # without an illustration the slot keeps the template's hatching, without its label
        hatch = "".join(f'<line x1="{x}" y1="0" x2="{x - HEIGHT}" y2="{HEIGHT}"/>' for x in range(SLOT_X, WIDTH + HEIGHT, 16))
        slot = f'<g stroke="{HALFTONE}" stroke-width="1.2">{hatch}</g>'
    view_box, lockup = svg_inner(LOCKUP.read_text())
    lockup_height = 48
    if style == "community":
        logo = community_logo(view_box, lockup)
    else:
        logo = (f'<svg x="{TITLE_X}" y="{HEIGHT - 64 - lockup_height}" width="{lockup_height * 7800 / 1550}" '
                f'height="{lockup_height}" viewBox="{view_box}">{lockup}</svg>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">'
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{PAPER}"/>'
            f'<clipPath id="s"><rect x="{SLOT_X}" width="{WIDTH - SLOT_X}" height="{HEIGHT}"/></clipPath>'
            f'<g clip-path="url(#s)">{slot}</g>'
            f'<text x="{TITLE_X}" y="112" font-family="Inter Tight" font-weight="700" font-size="22" letter-spacing="2.5" '
            f'fill="{VIOLET}">{html.escape(category.upper())}</text>'
            f'<text font-family="Inter Tight" font-weight="800" letter-spacing="-1.1" font-size="{TITLE_SIZE}" fill="{INK}">{tspans}</text>'
            f'{logo}</svg>')


def community_logo(view_box, lockup):
    """Symbol on the left; on its right the wordmark with "comunidad" above its start, like a sub-brand."""
    split = lockup.rfind("<path")  # the lockup is the symbol group followed by one wordmark path
    symbol, wordmark = lockup[:split], lockup[split:]
    size = 72
    scale = size / 1550  # same proportions as the horizontal lockup
    top, text_x = HEIGHT - 64 - size, TITLE_X + WORDMARK_BOX[0] * scale
    return (f'<svg x="{TITLE_X}" y="{top}" width="{size}" height="{size}" viewBox="0 0 1550 1550">{symbol}</svg>'
            f'<svg x="{text_x}" y="{top + 30}" width="{WORDMARK_BOX[2] * scale}" height="{WORDMARK_BOX[3] * scale}" '
            f'viewBox="{" ".join(map(str, WORDMARK_BOX))}">{wordmark}</svg>'
            # small tracked lowercase over the start of the wordmark reads as its descriptor
            f'<text x="{text_x}" y="{top + 21}" font-family="Inter Tight" font-weight="500" font-size="20" '
            f'letter-spacing="2" fill="{INK}">comunidad</text>')


def strip_png_metadata(data):
    out, i = [data[:8]], 8
    while i < len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        if data[i + 4:i + 8] in PNG_KEEP:
            out.append(data[i:i + 12 + length])
        i += 12 + length
    return b"".join(out)


def render_cover(category, title, image=None, image_format="png", style="article"):
    if image_format not in ("png", "webp"):
        raise InvalidCoverInput("format must be png or webp")
    png = strip_png_metadata(cairosvg.svg2png(bytestring=build_cover_svg(category, title, image, style).encode(), output_width=WIDTH))
    if image_format == "png":
        return png
    buffer = io.BytesIO()
    Image.open(io.BytesIO(png)).convert("RGB").save(buffer, "WEBP", quality=90, method=6)  # Pillow writes no EXIF or ICC here
    return buffer.getvalue()


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60] or "cover"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--category", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--style", choices=STYLES, default="article")
    parser.add_argument("--slug")
    parser.add_argument("--output", type=Path, default=Path("covers"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.output / f"{args.slug or slugify(args.title)}-cover"
    try:
        image = args.image.read_bytes() if args.image else None
        for image_format in ("png", "webp"):
            Path(f"{base}.{image_format}").write_bytes(render_cover(args.category, args.title, image, image_format, args.style))
    except InvalidCoverInput as error:
        sys.exit(f"cover: {error}")
    print(f"{base}.png\n{base}.webp")
