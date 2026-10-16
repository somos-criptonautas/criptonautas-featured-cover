"""End-to-end check against a running container:
SERVICE_URL=http://127.0.0.1:8000 COVER_TOKEN=<token> python tests/service_check.py"""
import io
import json
import os
import urllib.error
import urllib.request

from PIL import Image

BASE_URL = os.environ.get("SERVICE_URL", "http://127.0.0.1:8000")
TOKEN = os.environ["COVER_TOKEN"]


def call(path, body=None, token=TOKEN):
    request = urllib.request.Request(BASE_URL + path, data=body, method="POST" if body is not None else "GET",
                                     headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


good = json.dumps({"category": "Curso", "title": "Qué es una wallet", "format": "webp"}).encode()
assert call("/health")[:2] == (200, b"ok")
code, webp, headers = call("/cover", good)
assert code == 200, (code, webp[:200])
image = Image.open(io.BytesIO(webp))
assert (image.format, image.size) == ("WEBP", (1200, 630)), (image.format, image.size)
assert not {"exif", "icc_profile", "xmp"} & set(image.info), image.info
assert headers["Content-Disposition"] == 'attachment; filename="cover.webp"', headers["Content-Disposition"]
assert call("/cover", good, token="wrong")[0] == 401
assert call("/cover", b"x" * 5000)[0] == 413
assert call("/cover", b'{"category": "Curso", "title": "x", "image": "AAAA"}')[0] == 422
print("ok")
