from pathlib import Path
import tempfile
import unittest

from autoplay.image_match import ImageError, crop_png_file, match_template_file, read_png
from autoplay.script import Region
from png_helpers import write_rgba_png

BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
BLUE = (0, 0, 255, 255)
WHITE = (255, 255, 255, 255)


class ImageMatchTest(unittest.TestCase):
    def test_read_png_and_match_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(
                source,
                3,
                3,
                [
                    BLACK,
                    BLACK,
                    BLACK,
                    BLACK,
                    RED,
                    GREEN,
                    BLACK,
                    BLUE,
                    WHITE,
                ],
            )
            write_rgba_png(template, 2, 2, [RED, GREEN, BLUE, WHITE])

            loaded = read_png(source)
            match = match_template_file(source, template, threshold=1.0)

            self.assertEqual((loaded.width, loaded.height), (3, 3))
            self.assertTrue(match.matched)
            self.assertEqual((match.x, match.y), (1, 1))

    def test_crop_png_file_writes_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(
                source,
                3,
                2,
                [
                    RED,
                    GREEN,
                    BLUE,
                    WHITE,
                    RED,
                    GREEN,
                ],
            )

            crop = crop_png_file(source, template, x=1, y=0, width=2, height=2)
            written = read_png(template)

            self.assertEqual((crop.width, crop.height), (2, 2))
            self.assertEqual((written.width, written.height), (2, 2))
            self.assertEqual(written.pixel(0, 0), GREEN)
            self.assertEqual(written.pixel(1, 0), BLUE)
            self.assertEqual(written.pixel(0, 1), RED)
            self.assertEqual(written.pixel(1, 1), GREEN)

    def test_crop_png_rejects_out_of_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            write_rgba_png(source, 1, 1, [RED])

            with self.assertRaisesRegex(ImageError, "outside"):
                crop_png_file(source, tmp_path / "template.png", x=0, y=0, width=2, height=1)

    def test_region_limits_search_area(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 3, 3, [BLACK, BLACK, BLACK, BLACK, RED, BLACK, BLACK, BLACK, BLACK])
            write_rgba_png(template, 1, 1, [RED])

            match = match_template_file(source, template, threshold=1.0, region=Region(x=0, y=0, width=1, height=1))

            self.assertFalse(match.matched)

    def test_threshold_failure_reports_best_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [RED])
            write_rgba_png(template, 1, 1, [BLUE])

            match = match_template_file(source, template, threshold=1.0)

            self.assertFalse(match.matched)
            self.assertEqual(match.score, 0.0)

    def test_non_png_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "not.png"
            path.write_bytes(b"not a png")

            with self.assertRaisesRegex(ImageError, "Not a PNG"):
                read_png(path)

    def test_large_fuzzy_search_fails_fast_after_exact_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 80, 80, [BLACK] * 6400)
            write_rgba_png(template, 20, 20, [RED] * 400)

            with self.assertRaisesRegex(ImageError, "fuzzy search is too large"):
                match_template_file(source, template, threshold=0.95)

    def test_region_allows_small_fuzzy_search_after_exact_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 80, 80, [BLACK] * 6400)
            write_rgba_png(template, 20, 20, [RED] * 400)

            match = match_template_file(source, template, threshold=0.95, region=Region(x=0, y=0, width=20, height=20))

            self.assertFalse(match.matched)


if __name__ == "__main__":
    unittest.main()
