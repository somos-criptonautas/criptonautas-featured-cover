import http.client
import io
import json
import os
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cover import HEIGHT, PNG_KEEP, WIDTH, InvalidCoverInput, render_cover, wrap_title  # noqa: E402
from server import Handler  # noqa: E402


def png_chunk_types(data):
    i, types = 8, set()
    while i < len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        types.add(data[i + 4:i + 8])
        i += 12 + length
    return types


class CoverTest(unittest.TestCase):
    def test_title_wrapping(self):
        self.assertEqual(wrap_title("Qué es una wallet"), ["Qué es una wallet"])
        self.assertEqual(len(wrap_title("Cómo leer el volumen sin confundirlo con la tendencia")), 3)

    def test_rejects_titles_that_do_not_fit(self):
        for title in ("x" * 141, "palabra " * 40):
            with self.assertRaises(InvalidCoverInput):
                render_cover("Curso", title)

    def test_png_has_no_metadata_and_text_stays_left_of_the_slot(self):
        png = render_cover("Análisis técnico", "Soportes & <resistencias> en marcos cortos")
        image = Image.open(io.BytesIO(png))
        self.assertEqual(image.size, (WIDTH, HEIGHT))
        self.assertLessEqual(png_chunk_types(png), PNG_KEEP)
        rgb = image.convert("RGB")
        self.assertTrue(all(rgb.getpixel((x, y)) == (232, 230, 225) for x in range(700, 760) for y in range(140, 360)))

    def test_illustration_fills_the_slot(self):
        art = io.BytesIO()
        Image.new("RGB", (800, 800), "#5814EA").save(art, "JPEG")
        webp = Image.open(io.BytesIO(render_cover("Curso", "Con ilustración", art.getvalue(), "webp")))
        self.assertGreater(webp.getpixel((1000, 300))[2], 150)
        self.assertFalse({"exif", "icc_profile", "xmp"} & set(webp.info))

    def test_community_style_has_no_metadata_and_keeps_the_slot_clear(self):
        png = render_cover("Curso de trading", "Cómo leer el volumen sin confundirlo con la tendencia", style="community")
        self.assertLessEqual(png_chunk_types(png), PNG_KEEP)
        rgb = Image.open(io.BytesIO(png)).convert("RGB")
        self.assertTrue(all(rgb.getpixel((x, y)) == (232, 230, 225) for x in range(700, 760) for y in range(140, 360)))
        self.assertNotEqual(png, render_cover("Curso de trading", "Cómo leer el volumen sin confundirlo con la tendencia"))

    def test_rejects_unknown_style(self):
        with self.assertRaises(InvalidCoverInput):
            render_cover("Curso", "Prueba", style="poster")

    def test_rejects_svg_as_illustration(self):
        with self.assertRaises(InvalidCoverInput):
            render_cover("Curso", "Imagen falsa", b"<svg onload=1>")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.token = b"t" * 32
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def post(self, body, authorization="Bearer " + "t" * 32, path="/cover"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=20)
        connection.request("POST", path, body, {"Authorization": authorization})
        response = connection.getresponse()
        response.read()
        connection.close()
        return response

    def test_responses(self):
        good = json.dumps({"category": "Curso", "title": "Prueba", "format": "webp"})
        response = self.post(good)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Content-Disposition"], 'attachment; filename="cover.webp"')
        self.assertEqual(self.post(good, "Bearer wrong").status, 401)
        self.assertEqual(self.post(good, "").status, 401)
        self.assertEqual(self.post(good, path="/unknown").status, 404)
        self.assertEqual(self.post("x" * 5000).status, 413)
        self.assertEqual(self.post('{"category": "Curso", "title": "x", "image": "AAAA"}').status, 422)
        self.assertEqual(self.post("not json").status, 422)
        community = json.dumps({"category": "Wiki · Monero", "title": "Prueba", "style": "community"})
        self.assertEqual(self.post(community).status, 200)
        self.assertEqual(self.post(json.dumps({"category": "Curso", "title": "x", "style": "poster"})).status, 422)


if __name__ == "__main__":
    unittest.main()
